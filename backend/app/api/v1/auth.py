from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user, get_current_session, require_permissions
from app.infrastructure.database import get_db
from app.models.user import User, UserSession
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    ProtectedRouteResponse,
    RefreshTokenRequest,
    RegisterRequest,
    SessionResponse,
    SessionsListResponse,
    TrustedDeviceResponse,
    TrustedDevicesListResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    return service.register_user(payload, request)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    return service.authenticate_user(payload, request)


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AuthResponse:
    service = AuthService(db)
    return service.refresh_access_token(payload, request)


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    current_session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    service = AuthService(db)
    return service.logout_user(
        current_user=current_user,
        current_session=current_session,
        payload=payload,
        request=request,
    )


@router.get("/sessions", response_model=SessionsListResponse)
def list_sessions(
    current_user: User = Depends(require_permissions("sessions:read_own")),
    current_session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> SessionsListResponse:
    service = AuthService(db)
    return service.list_sessions(current_user=current_user, current_session=current_session)


@router.delete("/sessions/{session_id}", response_model=SessionResponse)
def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(require_permissions("sessions:revoke_own")),
    db: Session = Depends(get_db),
) -> SessionResponse:
    service = AuthService(db)
    return service.revoke_session(current_user=current_user, session_id=session_id, request=request)


@router.get("/devices", response_model=TrustedDevicesListResponse)
def list_devices(
    current_user: User = Depends(require_permissions("devices:read_own")),
    db: Session = Depends(get_db),
) -> TrustedDevicesListResponse:
    service = AuthService(db)
    return service.list_trusted_devices(current_user=current_user)


@router.delete("/devices/{device_id}", response_model=TrustedDeviceResponse)
def revoke_device(
    device_id: str,
    request: Request,
    current_user: User = Depends(require_permissions("devices:read_own")),
    db: Session = Depends(get_db),
) -> TrustedDeviceResponse:
    service = AuthService(db)
    return service.revoke_trusted_device(current_user=current_user, device_id=device_id, request=request)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    service = AuthService(db)
    return service._build_user_response(current_user)


@router.get("/protected", response_model=ProtectedRouteResponse)
def protected_route(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProtectedRouteResponse:
    service = AuthService(db)
    return ProtectedRouteResponse(
        message="Authenticated access granted.",
        user=service._build_user_response(current_user),
    )
