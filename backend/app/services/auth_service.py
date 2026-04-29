# Copyright (c) 2026 Guilherme Michael
# Licensed under the MIT License

from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    coerce_utc,
    has_permission,
    get_password_hash,
    get_role_permissions,
    hash_secret,
    utc_now,
    verify_password,
)
from app.models.user import BiometricProfile, LoginAttempt, Organization, TrustedDevice, User, UserSession
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SessionResponse,
    SessionsListResponse,
    TrustedDeviceResponse,
    TrustedDevicesListResponse,
    UserResponse,
)
from app.services.audit_service import AuditService
from app.services.device_service import DeviceService
from app.services.rate_limit_service import rate_limiter
from app.services.session_service import SessionService

settings = get_settings()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.session_service = SessionService(db)
        self.device_service = DeviceService(db)

    def register_user(self, payload: RegisterRequest, request: Request) -> AuthResponse:
        request_metadata = self.audit_service.extract_request_metadata(request)
        self._enforce_auth_rate_limits(email=payload.email, request_metadata=request_metadata, scope="register")

        existing_user = self._get_user_by_email(payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        organization, role = self._resolve_registration_organization(payload)
        user = User(
            organization_id=organization.id,
            full_name=payload.full_name,
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            role=role,
        )
        self.db.add(user)
        self.db.flush()

        biometric_profile = BiometricProfile(
            organization_id=organization.id,
            user_id=user.id,
            phrase_secret=settings.default_checkin_phrase,
            face_model_version="demo-face-v1",
            voice_model_version="demo-voice-v1",
            consent_version="1.0",
        )
        self.db.add(biometric_profile)

        tokens = self.session_service.create_session(
            user=user,
            request_metadata=request_metadata,
            raw_device_fingerprint=request_metadata.device_fingerprint,
        )
        self.device_service.register_device_event(
            user=user,
            request_metadata=request_metadata,
            raw_fingerprint=request_metadata.device_fingerprint,
            trust_device=bool(request_metadata.device_fingerprint),
        )

        self.audit_service.create_audit_log(
            action="auth.register",
            severity="info",
            request=request,
            user=user,
            organization=organization,
            entity_name="user",
            entity_id=user.id,
            new_data={"email": user.email, "role": user.role, "session_id": tokens.session.id},
        )

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(tokens.session)
        return self._build_auth_response(user=user, session=tokens.session, access_token=tokens.access_token, refresh_token=tokens.refresh_token)

    def authenticate_user(self, payload: LoginRequest, request: Request) -> AuthResponse:
        request_metadata = self.audit_service.extract_request_metadata(request)
        self._enforce_auth_rate_limits(email=payload.email, request_metadata=request_metadata, scope="login")

        user = self._get_user_by_email(payload.email, organization_slug=payload.organization_slug)
        if user is None:
            self._record_login_attempt(
                user=None,
                organization=None,
                request=request,
                email_attempted=payload.email,
                status_value="denied",
                denial_reason="invalid_credentials",
            )
            self.audit_service.create_audit_log(
                action="auth.login_failed",
                severity="warning",
                request=request,
                entity_name="user",
                new_data={"email_attempted": payload.email, "reason": "invalid_credentials"},
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email, organization or password.",
            )

        self._ensure_user_can_authenticate(user, request, payload.email)

        if not verify_password(payload.password, user.password_hash):
            self._handle_failed_login(user, request, payload.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email, organization or password.",
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = utc_now()

        assessment = self.device_service.assess_device(
            user=user,
            raw_fingerprint=request_metadata.device_fingerprint,
        )
        first_known_device = not bool(user.trusted_devices)
        trusted_device = self.device_service.register_device_event(
            user=user,
            request_metadata=request_metadata,
            raw_fingerprint=request_metadata.device_fingerprint,
            trust_device=first_known_device,
        )
        tokens = self.session_service.create_session(
            user=user,
            request_metadata=request_metadata,
            raw_device_fingerprint=request_metadata.device_fingerprint,
        )

        self._record_login_attempt(
            user=user,
            organization=user.organization,
            session=tokens.session,
            request=request,
            email_attempted=payload.email,
            status_value="approved",
        )
        self.audit_service.create_audit_log(
            action="auth.login_succeeded",
            severity="info",
            request=request,
            user=user,
            organization=user.organization,
            entity_name="user_session",
            entity_id=tokens.session.id,
            new_data={
                "email_attempted": payload.email,
                "new_device_detected": not assessment.is_known and assessment.fingerprint_hash is not None,
                "device_trusted": trusted_device.is_trusted if trusted_device else False,
            },
        )

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(tokens.session)
        return self._build_auth_response(user=user, session=tokens.session, access_token=tokens.access_token, refresh_token=tokens.refresh_token)

    def refresh_access_token(self, payload: RefreshTokenRequest, request: Request) -> AuthResponse:
        request_metadata = self.audit_service.extract_request_metadata(request)
        rate_limiter.enforce(
            scope="auth-refresh-ip",
            key=request_metadata.ip_address or "unknown",
            limit=settings.rate_limit_refresh_per_10_minutes,
            window_seconds=600,
        )

        token_bundle = self.session_service.rotate_refresh_token(refresh_token=payload.refresh_token)
        user = self.db.get(User, token_bundle.session.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User for refresh token was not found.",
            )

        self._ensure_user_can_authenticate(user, request, user.email, count_as_failure=False)
        self.audit_service.create_audit_log(
            action="auth.refresh_token",
            severity="info",
            request=request,
            user=user,
            organization=user.organization,
            entity_name="user_session",
            entity_id=token_bundle.session.id,
            new_data={"rotation_counter": token_bundle.session.rotation_counter},
        )

        self.db.commit()
        self.db.refresh(user)
        self.db.refresh(token_bundle.session)
        return self._build_auth_response(
            user=user,
            session=token_bundle.session,
            access_token=token_bundle.access_token,
            refresh_token=token_bundle.refresh_token,
        )

    def logout_user(
        self,
        *,
        current_user: User,
        current_session: UserSession,
        payload: LogoutRequest,
        request: Request,
    ) -> dict[str, object]:
        revoked_count = 0
        if payload.revoke_all:
            sessions = self.session_service.list_sessions(current_user=current_user, allow_any=False)
            for session in sessions:
                if session.revoked_at is None:
                    self.session_service.revoke_session(session=session, reason="user_logout_all")
                    revoked_count += 1
        else:
            if current_session.revoked_at is None:
                self.session_service.revoke_session(session=current_session, reason="user_logout")
                revoked_count = 1

        self.audit_service.create_audit_log(
            action="auth.logout",
            severity="info",
            request=request,
            user=current_user,
            organization=current_user.organization,
            entity_name="user_session",
            entity_id=current_session.id,
            new_data={"revoke_all": payload.revoke_all, "revoked_count": revoked_count},
        )
        self.db.commit()
        return {"status": "revoked", "revoked_count": revoked_count}

    def list_sessions(self, *, current_user: User, current_session: UserSession) -> SessionsListResponse:
        allow_any = has_permission(current_user.role, "sessions:read_all")
        sessions = self.session_service.list_sessions(current_user=current_user, allow_any=allow_any)
        return SessionsListResponse(
            items=[
                SessionResponse(
                    id=session.id,
                    user_id=session.user_id,
                    organization_id=session.organization_id,
                    rotation_counter=session.rotation_counter,
                    ip_address=session.ip_address,
                    user_agent=session.user_agent,
                    created_at=session.created_at,
                    last_used_at=session.last_used_at,
                    expires_at=session.expires_at,
                    revoked_at=session.revoked_at,
                    revoked_reason=session.revoked_reason,
                    is_current=session.id == current_session.id,
                )
                for session in sessions
            ]
        )

    def revoke_session(
        self,
        *,
        current_user: User,
        session_id: str,
        request: Request,
    ) -> SessionResponse:
        allow_any = has_permission(current_user.role, "sessions:revoke_any")
        session = self.session_service.revoke_user_session(
            current_user=current_user,
            session_id=session_id,
            allow_any=allow_any,
        )
        self.audit_service.create_audit_log(
            action="auth.session_revoked",
            severity="warning",
            request=request,
            user=current_user,
            organization=current_user.organization,
            entity_name="user_session",
            entity_id=session.id,
            new_data={"revoked_reason": session.revoked_reason},
        )
        self.db.commit()
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            organization_id=session.organization_id,
            rotation_counter=session.rotation_counter,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at,
            last_used_at=session.last_used_at,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
            revoked_reason=session.revoked_reason,
            is_current=False,
        )

    def list_trusted_devices(self, *, current_user: User) -> TrustedDevicesListResponse:
        devices = self.device_service.list_devices(user=current_user)
        return TrustedDevicesListResponse(
            items=[
                TrustedDeviceResponse(
                    id=device.id,
                    user_id=device.user_id,
                    organization_id=device.organization_id,
                    fingerprint_preview=device.fingerprint_preview,
                    display_name=device.display_name,
                    is_trusted=device.is_trusted,
                    first_seen_at=device.first_seen_at,
                    last_seen_at=device.last_seen_at,
                    last_ip_address=device.last_ip_address,
                    last_user_agent=device.last_user_agent,
                )
                for device in devices
            ]
        )

    def revoke_trusted_device(self, *, current_user: User, device_id: str, request: Request) -> TrustedDeviceResponse:
        device = self.device_service.revoke_device(user=current_user, device_id=device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trusted device was not found.",
            )
        self.audit_service.create_audit_log(
            action="auth.device_revoked",
            severity="warning",
            request=request,
            user=current_user,
            organization=current_user.organization,
            entity_name="trusted_device",
            entity_id=device.id,
            new_data={"is_trusted": device.is_trusted},
        )
        self.db.commit()
        return TrustedDeviceResponse(
            id=device.id,
            user_id=device.user_id,
            organization_id=device.organization_id,
            fingerprint_preview=device.fingerprint_preview,
            display_name=device.display_name,
            is_trusted=device.is_trusted,
            first_seen_at=device.first_seen_at,
            last_seen_at=device.last_seen_at,
            last_ip_address=device.last_ip_address,
            last_user_agent=device.last_user_agent,
        )

    def _build_auth_response(
        self,
        *,
        user: User,
        session: UserSession,
        access_token: str,
        refresh_token: str,
    ) -> AuthResponse:
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            access_token_expires_in=settings.access_token_expire_minutes * 60,
            refresh_token_expires_in=int(timedelta(days=settings.refresh_token_expire_days).total_seconds()),
            session_id=session.id,
            user=self._build_user_response(user),
        )

    def _build_user_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            status=user.status,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            created_at=user.created_at,
            updated_at=user.updated_at,
            permissions=sorted(get_role_permissions(user.role)),
            organization=user.organization,
        )

    def _get_user_by_email(self, email: str, organization_slug: str | None = None) -> User | None:
        query = select(User).where(User.email == email.lower())
        if organization_slug:
            query = query.join(Organization).where(Organization.slug == organization_slug.lower())
        return self.db.scalar(query)

    def _resolve_registration_organization(self, payload: RegisterRequest) -> tuple[Organization, str]:
        if payload.organization_slug:
            existing = self.db.scalar(select(Organization).where(Organization.slug == payload.organization_slug.lower()))
            if existing is not None:
                return existing, "viewer"

        slug_seed = payload.organization_slug or payload.organization_name or f"{payload.full_name.split()[0]} workspace"
        organization_name = payload.organization_name or f"{payload.full_name.split()[0]} Workspace"
        slug = self._unique_slug(self._slugify(slug_seed))
        organization = Organization(name=organization_name, slug=slug)
        self.db.add(organization)
        self.db.flush()
        return organization, "organization_owner"

    def _slugify(self, value: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
        normalized = base.strip("-") or "biogate-tenant"
        return normalized[:100]

    def _unique_slug(self, slug_base: str) -> str:
        slug = slug_base
        counter = 1
        while self.db.scalar(select(Organization.id).where(Organization.slug == slug)) is not None:
            counter += 1
            suffix = f"-{counter}"
            slug = f"{slug_base[:100 - len(suffix)]}{suffix}"
        return slug

    def _ensure_user_can_authenticate(
        self,
        user: User,
        request: Request,
        email_attempted: str,
        count_as_failure: bool = True,
    ) -> None:
        if user.organization.is_active is False:
            self._record_login_attempt(
                user=user,
                organization=user.organization,
                request=request,
                email_attempted=email_attempted,
                status_value="denied",
                denial_reason="organization_inactive",
            )
            self.audit_service.create_audit_log(
                action="auth.login_denied",
                severity="warning",
                request=request,
                user=user,
                organization=user.organization,
                entity_name="organization",
                entity_id=user.organization_id,
                new_data={"reason": "organization_inactive"},
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is not active.",
            )

        if user.status != "active":
            self._record_login_attempt(
                user=user,
                organization=user.organization,
                request=request,
                email_attempted=email_attempted,
                status_value="denied",
                denial_reason="inactive_user",
            )
            self.audit_service.create_audit_log(
                action="auth.login_denied",
                severity="warning",
                request=request,
                user=user,
                organization=user.organization,
                entity_name="user",
                entity_id=user.id,
                new_data={"reason": "inactive_user"},
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active.",
            )

        locked_until = coerce_utc(user.locked_until)
        if locked_until and locked_until > utc_now():
            self._record_login_attempt(
                user=user,
                organization=user.organization,
                request=request,
                email_attempted=email_attempted,
                status_value="locked",
                denial_reason="account_locked",
            )
            self.audit_service.create_audit_log(
                action="auth.login_locked",
                severity="warning",
                request=request,
                user=user,
                organization=user.organization,
                entity_name="user",
                entity_id=user.id,
                new_data={"reason": "account_locked", "locked_until": locked_until.isoformat()},
            )
            if count_as_failure:
                user.updated_at = utc_now()
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="User account is temporarily locked.",
            )

    def _handle_failed_login(self, user: User, request: Request, email_attempted: str) -> None:
        user.failed_login_attempts += 1
        user.updated_at = utc_now()

        denial_reason = "invalid_credentials"
        status_value = "denied"

        if user.failed_login_attempts >= settings.auth_max_failed_attempts:
            user.locked_until = utc_now() + timedelta(minutes=settings.auth_lockout_minutes)
            denial_reason = "account_locked"
            status_value = "locked"
            self.audit_service.create_risk_event(
                user=user,
                event_type="auth.lockout",
                risk_level="high",
                score=Decimal("0.85"),
                description="Account temporarily locked after repeated failed login attempts.",
                metadata_json={
                    "failed_login_attempts": user.failed_login_attempts,
                    "lockout_minutes": settings.auth_lockout_minutes,
                },
            )

        self._record_login_attempt(
            user=user,
            organization=user.organization,
            request=request,
            email_attempted=email_attempted,
            status_value=status_value,
            denial_reason=denial_reason,
        )
        self.audit_service.create_audit_log(
            action="auth.login_failed",
            severity="warning",
            request=request,
            user=user,
            organization=user.organization,
            entity_name="user",
            entity_id=user.id,
            new_data={
                "reason": denial_reason,
                "failed_login_attempts": user.failed_login_attempts,
            },
        )
        self.db.commit()

    def _record_login_attempt(
        self,
        *,
        user: User | None,
        organization: Organization | None,
        request: Request,
        email_attempted: str,
        status_value: str,
        denial_reason: str | None = None,
        session: UserSession | None = None,
    ) -> None:
        request_metadata = self.audit_service.extract_request_metadata(request)
        attempt = LoginAttempt(
            organization_id=organization.id if organization else user.organization_id if user else None,
            user_id=user.id if user else None,
            session_id=session.id if session else None,
            email_attempted=email_attempted,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
            device_fingerprint=request_metadata.device_fingerprint,
            status=status_value,
            denial_reason=denial_reason,
            request_id=request_metadata.request_id,
            trace_id=request_metadata.trace_id,
            correlation_id=request_metadata.correlation_id,
        )
        self.db.add(attempt)

    def _enforce_auth_rate_limits(self, *, email: str, request_metadata, scope: str) -> None:
        rate_limiter.enforce(
            scope=f"{scope}-ip",
            key=request_metadata.ip_address or "unknown",
            limit=settings.rate_limit_login_per_15_minutes,
            window_seconds=900,
        )
        rate_limiter.enforce(
            scope=f"{scope}-email",
            key=email.lower(),
            limit=settings.rate_limit_login_per_15_minutes,
            window_seconds=900,
        )
