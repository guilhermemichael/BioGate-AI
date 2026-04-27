from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    LoginRequest,
    ProtectedRouteResponse,
    RefreshTokenRequest,
    RegisterRequest,
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


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh_token(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    service = AuthService(db)
    return service.refresh_access_token(payload.refresh_token, request)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get("/protected", response_model=ProtectedRouteResponse)
def protected_route(current_user: User = Depends(get_current_active_user)) -> ProtectedRouteResponse:
    return ProtectedRouteResponse(
        message="Authenticated access granted.",
        user=UserResponse.model_validate(current_user),
    )
