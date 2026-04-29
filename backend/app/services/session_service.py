from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import coerce_utc, create_access_token, create_refresh_token, decode_token, hash_secret, utc_now
from app.models.user import User, UserSession
from app.services.audit_service import RequestMetadata

settings = get_settings()


@dataclass(slots=True)
class SessionTokenBundle:
    access_token: str
    refresh_token: str
    session: UserSession


class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        *,
        user: User,
        request_metadata: RequestMetadata,
        raw_device_fingerprint: str | None,
    ) -> SessionTokenBundle:
        placeholder_session = UserSession(
            organization_id=user.organization_id,
            user_id=user.id,
            refresh_token_hash="pending",
            device_fingerprint_hash=hash_secret(raw_device_fingerprint) if raw_device_fingerprint else None,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
            created_at=utc_now(),
            last_used_at=utc_now(),
            expires_at=utc_now() + timedelta(days=settings.refresh_token_expire_days),
        )
        self.db.add(placeholder_session)
        self.db.flush()

        access_token = create_access_token(
            subject=user.id,
            role=user.role,
            organization_id=user.organization_id,
            session_id=placeholder_session.id,
        )
        refresh_token = create_refresh_token(
            subject=user.id,
            role=user.role,
            organization_id=user.organization_id,
            session_id=placeholder_session.id,
        )
        placeholder_session.refresh_token_hash = hash_secret(refresh_token)
        placeholder_session.last_used_at = utc_now()
        return SessionTokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            session=placeholder_session,
        )

    def rotate_refresh_token(self, *, refresh_token: str) -> SessionTokenBundle:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token required.",
            )

        session_id = payload.get("sid")
        subject = payload.get("sub")
        organization_id = payload.get("org")
        if not session_id or not subject or not organization_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token payload is incomplete.",
            )

        session = self.db.get(UserSession, session_id)
        if session is None or session.user_id != subject or session.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session is invalid.",
            )

        session_expires_at = coerce_utc(session.expires_at)
        if session.revoked_at is not None or (session_expires_at is not None and session_expires_at <= utc_now()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh session is no longer active.",
            )

        candidate_hash = hash_secret(refresh_token)
        if candidate_hash != session.refresh_token_hash:
            session.revoked_at = utc_now()
            session.revoked_reason = "refresh_replay_detected"
            self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token replay detected. Session revoked.",
            )

        user = self.db.get(User, session.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User for refresh token was not found.",
            )

        new_access_token = create_access_token(
            subject=user.id,
            role=user.role,
            organization_id=user.organization_id,
            session_id=session.id,
        )
        new_refresh_token = create_refresh_token(
            subject=user.id,
            role=user.role,
            organization_id=user.organization_id,
            session_id=session.id,
        )
        session.refresh_token_hash = hash_secret(new_refresh_token)
        session.rotation_counter += 1
        session.last_used_at = utc_now()
        session.expires_at = utc_now() + timedelta(days=settings.refresh_token_expire_days)
        return SessionTokenBundle(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            session=session,
        )

    def revoke_session(self, *, session: UserSession, reason: str) -> UserSession:
        session.revoked_at = utc_now()
        session.revoked_reason = reason
        session.last_used_at = utc_now()
        return session

    def revoke_user_session(
        self,
        *,
        current_user: User,
        session_id: str,
        allow_any: bool,
    ) -> UserSession:
        query = select(UserSession).where(
            UserSession.id == session_id,
            UserSession.organization_id == current_user.organization_id,
        )
        if not allow_any:
            query = query.where(UserSession.user_id == current_user.id)
        session = self.db.scalar(query)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session was not found.",
            )
        return self.revoke_session(session=session, reason="manual_revocation")

    def list_sessions(self, *, current_user: User, allow_any: bool) -> list[UserSession]:
        query = select(UserSession).where(UserSession.organization_id == current_user.organization_id)
        if not allow_any:
            query = query.where(UserSession.user_id == current_user.id)
        query = query.order_by(UserSession.last_used_at.desc())
        return list(self.db.scalars(query).all())
