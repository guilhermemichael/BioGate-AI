from datetime import datetime

from pydantic import BaseModel


class SecurityLogItem(BaseModel):
    attempt_id: str
    user_id: str | None
    user_name: str | None
    user_email: str | None
    status: str
    risk_level: str | None
    face_score: float | None
    voice_score: float | None
    phrase_score: float | None
    liveness_score: float | None
    risk_score: float | None
    final_confidence: float | None
    ip_address: str | None
    user_agent: str | None
    device_fingerprint: str | None
    reasons: list[str]
    denial_reason: str | None
    recommended_action: str | None
    created_at: datetime


class SecurityLogsListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[SecurityLogItem]


class RelatedAuditEvent(BaseModel):
    id: str
    action: str
    severity: str
    created_at: datetime
    ip_address: str | None
    user_agent: str | None
    new_data: dict | None


class SecurityLogDetailResponse(BaseModel):
    attempt: SecurityLogItem
    related_audit_events: list[RelatedAuditEvent]
