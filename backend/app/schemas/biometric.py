from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BiometricCheckInRequest(BaseModel):
    spoken_phrase: str = Field(min_length=3, max_length=280)
    expected_phrase: str = Field(
        default="I authorize this access.",
        min_length=3,
        max_length=280,
    )
    face_capture_quality: float = Field(default=0.91, ge=0.0, le=1.0)
    voice_capture_quality: float = Field(default=0.84, ge=0.0, le=1.0)
    liveness_hint: float = Field(default=0.88, ge=0.0, le=1.0)
    device_fingerprint: str | None = Field(default=None, max_length=512)
    device_trusted: bool = True
    network_trusted: bool = True
    unusual_time: bool = False
    location_changed: bool = False

    @field_validator("spoken_phrase", "expected_phrase")
    @classmethod
    def strip_phrase(cls, value: str) -> str:
        return value.strip()


class BiometricAttemptResponse(BaseModel):
    attempt_id: str
    user_id: str | None
    email_attempted: str | None
    face_score: float | None
    voice_score: float | None
    phrase_score: float | None
    liveness_score: float | None
    risk_score: float | None
    final_confidence: float | None
    risk_level: str | None
    status: str
    reasons: list[str]
    recommended_action: str | None
    denial_reason: str | None
    ip_address: str | None
    user_agent: str | None
    device_fingerprint: str | None
    created_at: datetime


class BiometricAttemptsListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[BiometricAttemptResponse]


class BiometricDecisionEnvelope(BaseModel):
    attempt: BiometricAttemptResponse


class RiskLevelExplanation(BaseModel):
    risk_level: Literal["low", "medium", "high", "critical"]
    risk_score: float
    reasons: list[str]
