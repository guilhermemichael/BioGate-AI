from datetime import date

from pydantic import BaseModel

from app.schemas.biometric import BiometricAttemptResponse


class DashboardSummaryResponse(BaseModel):
    total_attempts: int
    approved: int
    denied: int
    manual_review: int
    average_confidence: float
    average_risk: float


class DashboardRecentAttemptsResponse(BaseModel):
    items: list[BiometricAttemptResponse]


class RiskDistributionItem(BaseModel):
    risk_level: str
    count: int


class RiskDistributionResponse(BaseModel):
    items: list[RiskDistributionItem]


class ConfidenceTrendPoint(BaseModel):
    day: date
    average_confidence: float
    average_risk: float
    total_attempts: int


class ConfidenceTrendResponse(BaseModel):
    items: list[ConfidenceTrendPoint]
