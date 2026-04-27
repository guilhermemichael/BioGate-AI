from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.biometric import (
    BiometricAttemptResponse,
    BiometricAttemptsListResponse,
    BiometricCheckInRequest,
)
from app.services.biometric_service import BiometricService

router = APIRouter(prefix="/biometric", tags=["biometric"])


@router.post("/check-in", response_model=BiometricAttemptResponse, status_code=status.HTTP_201_CREATED)
def biometric_check_in(
    payload: BiometricCheckInRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BiometricAttemptResponse:
    service = BiometricService(db)
    return service.create_check_in(user=current_user, payload=payload, request=request)


@router.get("/attempts", response_model=BiometricAttemptsListResponse)
def list_biometric_attempts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BiometricAttemptsListResponse:
    service = BiometricService(db)
    return service.list_attempts(current_user=current_user, limit=limit, offset=offset)


@router.get("/attempts/{attempt_id}", response_model=BiometricAttemptResponse)
def get_biometric_attempt(
    attempt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BiometricAttemptResponse:
    service = BiometricService(db)
    return service.get_attempt(current_user=current_user, attempt_id=attempt_id)
