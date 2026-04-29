from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.infrastructure.database import get_db
from app.models.user import User, UserSession

password_context = CryptContext(schemes=["argon2"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()

ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 10,
    "user": 20,
    "security_analyst": 40,
    "admin": 70,
    "organization_owner": 100,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "viewer": {
        "dashboard:read",
        "profile:read",
    },
    "user": {
        "attempts:read_own",
        "checkin:run",
        "devices:read_own",
        "profile:read",
        "sessions:read_own",
        "sessions:revoke_own",
    },
    "security_analyst": {
        "attempts:read_all",
        "audit:read",
        "checkin:run",
        "dashboard:read",
        "profile:read",
        "reports:read",
        "risk:read",
    },
    "admin": {
        "attempts:read_all",
        "attempts:read_own",
        "audit:read",
        "checkin:run",
        "dashboard:read",
        "devices:read_all",
        "devices:read_own",
        "permissions:manage",
        "profile:read",
        "reports:read",
        "risk:read",
        "sessions:read_all",
        "sessions:read_own",
        "sessions:revoke_any",
        "sessions:revoke_own",
        "tenant:read",
        "users:manage",
    },
    "organization_owner": {
        "attempts:read_all",
        "attempts:read_own",
        "audit:read",
        "checkin:run",
        "dashboard:read",
        "devices:read_all",
        "devices:read_own",
        "permissions:manage",
        "profile:read",
        "reports:read",
        "risk:read",
        "sessions:read_all",
        "sessions:read_own",
        "sessions:revoke_any",
        "sessions:revoke_own",
        "tenant:manage",
        "tenant:read",
        "users:manage",
    },
}


@dataclass(slots=True)
class AuthenticatedContext:
    user_id: str
    organization_id: str
    role: str
    session_id: str
    permissions: set[str]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return password_context.hash(password)


def hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def get_role_permissions(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: str, permission: str) -> bool:
    return permission in get_role_permissions(role)


def create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    organization_id: str,
    role: str,
    session_id: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    issued_at = utc_now()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "org": organization_id,
        "role": role,
        "sid": session_id,
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": issued_at + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role: str, organization_id: str, session_id: str) -> str:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        organization_id=organization_id,
        role=role,
        session_id=session_id,
    )


def create_refresh_token(subject: str, role: str, organization_id: str, session_id: str) -> str:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        organization_id=organization_id,
        role=role,
        session_id=session_id,
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc


def require_permissions(*permissions: str):
    def dependency(
        request: Request,
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        context: AuthenticatedContext | None = getattr(request.state, "auth_context", None)
        granted = context.permissions if context is not None else get_role_permissions(current_user.role)
        missing = [permission for permission in permissions if permission not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing)}.",
            )
        return current_user

    return dependency


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
        )

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required.",
        )

    subject = payload.get("sub")
    organization_id = payload.get("org")
    session_id = payload.get("sid")
    role = payload.get("role")
    if not subject or not organization_id or not session_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is incomplete.",
        )

    user = db.get(User, subject)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user was not found.",
        )

    if user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tenant does not match the authenticated user.",
        )

    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user.id or session.organization_id != user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid.",
        )

    session_expires_at = coerce_utc(session.expires_at)
    if session.revoked_at is not None or (session_expires_at is not None and session_expires_at <= utc_now()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or has been revoked.",
        )

    request.state.auth_context = AuthenticatedContext(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
        session_id=session.id,
        permissions=get_role_permissions(user.role),
    )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active.",
        )

    locked_until = coerce_utc(current_user.locked_until)
    if locked_until and locked_until > utc_now():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="User account is temporarily locked.",
        )

    if current_user.organization.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not active.",
        )

    return current_user


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
) -> UserSession:
    context: AuthenticatedContext | None = getattr(request.state, "auth_context", None)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated session context is missing.",
        )

    session = db.get(UserSession, context.session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated session was not found.",
        )
    return session
