from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    utc_now,
    verify_password,
)
from app.models.user import LoginAttempt, User
from app.schemas.auth import AccessTokenResponse, AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.audit_service import AuditService

settings = get_settings()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def register_user(self, payload: RegisterRequest, request: Request) -> AuthResponse:
        existing_user = self._get_user_by_email(payload.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        user = User(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=get_password_hash(payload.password),
        )
        self.db.add(user)
        self.db.flush()

        self.audit_service.create_audit_log(
            action="auth.register",
            severity="info",
            request=request,
            user=user,
            entity_name="user",
            entity_id=user.id,
            new_data={"email": user.email, "role": user.role},
        )

        self.db.commit()
        self.db.refresh(user)
        return self._build_auth_response(user)

    def authenticate_user(self, payload: LoginRequest, request: Request) -> AuthResponse:
        user = self._get_user_by_email(payload.email)
        if user is None:
            self._record_login_attempt(
                user=None,
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
                detail="Invalid email or password.",
            )

        self._ensure_user_can_authenticate(user, request, payload.email)

        if not verify_password(payload.password, user.password_hash):
            self._handle_failed_login(user, request, payload.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = utc_now()

        self._record_login_attempt(
            user=user,
            request=request,
            email_attempted=payload.email,
            status_value="approved",
        )
        self.audit_service.create_audit_log(
            action="auth.login_succeeded",
            severity="info",
            request=request,
            user=user,
            entity_name="user",
            entity_id=user.id,
            new_data={"email_attempted": payload.email},
        )

        self.db.commit()
        self.db.refresh(user)
        return self._build_auth_response(user)

    def refresh_access_token(self, refresh_token: str, request: Request) -> AccessTokenResponse:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required.",
            )

        subject = payload.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token subject is missing.",
            )

        user = self.db.get(User, subject)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User for refresh token was not found.",
            )

        self._ensure_user_can_authenticate(user, request, user.email, count_as_failure=False)
        access_token = create_access_token(user.id, user.role)

        self.audit_service.create_audit_log(
            action="auth.refresh_token",
            severity="info",
            request=request,
            user=user,
            entity_name="user",
            entity_id=user.id,
            new_data={"email_attempted": user.email},
        )

        self.db.commit()
        return AccessTokenResponse(
            access_token=access_token,
            token_type="bearer",
            access_token_expires_in=settings.access_token_expire_minutes * 60,
        )

    def _build_auth_response(self, user: User) -> AuthResponse:
        return AuthResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id, user.role),
            token_type="bearer",
            access_token_expires_in=settings.access_token_expire_minutes * 60,
            refresh_token_expires_in=int(timedelta(days=settings.refresh_token_expire_days).total_seconds()),
            user=UserResponse.model_validate(user),
        )

    def _get_user_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email.lower())
        return self.db.scalar(query)

    def _ensure_user_can_authenticate(
        self,
        user: User,
        request: Request,
        email_attempted: str,
        count_as_failure: bool = True,
    ) -> None:
        if user.status != "active":
            self._record_login_attempt(
                user=user,
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
                entity_name="user",
                entity_id=user.id,
                new_data={"reason": "inactive_user"},
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active.",
            )

        if user.locked_until and user.locked_until > utc_now():
            self._record_login_attempt(
                user=user,
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
                entity_name="user",
                entity_id=user.id,
                new_data={"reason": "account_locked", "locked_until": user.locked_until.isoformat()},
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
        user: User | None,
        request: Request,
        email_attempted: str,
        status_value: str,
        denial_reason: str | None = None,
    ) -> None:
        request_metadata = self.audit_service.extract_request_metadata(request)
        attempt = LoginAttempt(
            user_id=user.id if user else None,
            email_attempted=email_attempted,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
            device_fingerprint=request_metadata.device_fingerprint,
            status=status_value,
            denial_reason=denial_reason,
        )
        self.db.add(attempt)
