from datetime import datetime

from pydantic import BaseModel


class SecurityLogItem(BaseModel):
    attempt_id: str
    organization_id: str | None
    user_id: str | None
    user_name: str | None
    user_email: str | None
    session_id: str | None
    status: str
    risk_level: str | None
    context_score: float | None
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
    risk_reasons: list[str]
    score_breakdown: dict | None
    denial_reason: str | None
    recommended_action: str | None
    replay_detected: bool
    request_id: str | None
    trace_id: str | None
    correlation_id: str | None
    created_at: datetime


class SecurityLogsListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[SecurityLogItem]


class RelatedAuditEvent(BaseModel):
    id: str
    organization_id: str | None
    action: str
    severity: str
    created_at: datetime
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    trace_id: str | None
    correlation_id: str | None
    previous_hash: str | None
    event_hash: str | None
    new_data: dict | None


class SecurityLogDetailResponse(BaseModel):
    attempt: SecurityLogItem
    related_audit_events: list[RelatedAuditEvent]
