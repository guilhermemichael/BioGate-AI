from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_permissions
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.logs import SecurityLogDetailResponse, SecurityLogsListResponse
from app.services.log_service import LogService

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=SecurityLogsListResponse)
def list_security_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_value: str | None = Query(default=None, alias="status"),
    risk_level: str | None = Query(default=None),
    user_query: str | None = Query(default=None, alias="user"),
    ip_address: str | None = Query(default=None, alias="ip"),
    device: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    current_user: User = Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
) -> SecurityLogsListResponse:
    return LogService(db).list_logs(
        current_user=current_user,
        limit=limit,
        offset=offset,
        status_value=status_value,
        risk_level=risk_level,
        user_query=user_query,
        ip_address=ip_address,
        device=device,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{attempt_id}", response_model=SecurityLogDetailResponse)
def get_security_log(
    attempt_id: str,
    current_user: User = Depends(require_permissions("audit:read")),
    db: Session = Depends(get_db),
) -> SecurityLogDetailResponse:
    return LogService(db).get_log_detail(current_user=current_user, attempt_id=attempt_id)
