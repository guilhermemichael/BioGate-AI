from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.schemas.dashboard import (
    ConfidenceTrendResponse,
    DashboardRecentAttemptsResponse,
    DashboardSummaryResponse,
    RiskDistributionResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    return DashboardService(db).get_summary(current_user)


@router.get("/recent-attempts", response_model=DashboardRecentAttemptsResponse)
def dashboard_recent_attempts(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardRecentAttemptsResponse:
    return DashboardService(db).get_recent_attempts(current_user, limit)


@router.get("/risk-distribution", response_model=RiskDistributionResponse)
def dashboard_risk_distribution(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> RiskDistributionResponse:
    return DashboardService(db).get_risk_distribution(current_user)


@router.get("/confidence-trend", response_model=ConfidenceTrendResponse)
def dashboard_confidence_trend(
    days: int = Query(default=7, ge=3, le=30),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ConfidenceTrendResponse:
    return DashboardService(db).get_confidence_trend(current_user, days)
