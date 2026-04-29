from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import utc_now
from app.models.user import LoginAttempt, User
from app.schemas.biometric import BiometricCheckInRequest
from app.services.audit_service import RequestMetadata
from app.services.device_service import DeviceAssessment


@dataclass(slots=True)
class ScoreBundle:
    face_score: float
    voice_score: float
    phrase_score: float
    liveness_score: float


@dataclass(slots=True)
class RiskEvaluation:
    risk_score: float
    risk_level: str
    context_score: float
    reasons: list[str]


class RiskService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_check_in(
        self,
        *,
        user: User,
        payload: BiometricCheckInRequest,
        request_metadata: RequestMetadata,
        scores: ScoreBundle,
        device_assessment: DeviceAssessment,
        replay_detected: bool,
    ) -> RiskEvaluation:
        risk_score = 0.12
        reasons: list[str] = []

        if device_assessment.fingerprint_hash is None:
            risk_score += 0.08
            reasons.append("device_fingerprint_missing")
        elif not device_assessment.is_known:
            risk_score += 0.18
            reasons.append("new_device_detected")
        elif not device_assessment.is_trusted:
            risk_score += 0.10
            reasons.append("device_not_yet_trusted")

        if not payload.network_trusted:
            risk_score += 0.14
            reasons.append("network_untrusted")

        if payload.unusual_time:
            risk_score += 0.08
            reasons.append("unusual_time_window")

        if payload.location_changed:
            risk_score += 0.10
            reasons.append("location_shift_detected")

        if payload.response_latency_ms < 450:
            risk_score += 0.12
            reasons.append("response_latency_too_fast")

        if replay_detected:
            risk_score += 0.20
            reasons.append("replay_pattern_detected")

        if scores.face_score < 0.82:
            risk_score += 0.10
            reasons.append("face_score_below_optimal")

        if scores.voice_score < 0.78:
            risk_score += 0.08
            reasons.append("low_voice_score")

        if scores.phrase_score < 0.85:
            risk_score += 0.12
            reasons.append("phrase_mismatch_detected")

        if scores.liveness_score < 0.82:
            risk_score += 0.12
            reasons.append("liveness_signal_weak")

        if user.failed_login_attempts > 0:
            risk_score += min(user.failed_login_attempts * 0.04, 0.16)
            reasons.append("recent_auth_failures")

        recent_attempts = self.db.scalars(
            select(LoginAttempt)
            .where(
                LoginAttempt.user_id == user.id,
                LoginAttempt.organization_id == user.organization_id,
                LoginAttempt.final_confidence.is_not(None),
            )
            .order_by(LoginAttempt.created_at.desc())
            .limit(10)
        ).all()
        recent_non_approved = sum(1 for attempt in recent_attempts if attempt.status != "approved")
        if recent_non_approved > 0:
            risk_score += min(recent_non_approved * 0.03, 0.12)
            reasons.append("recent_biometric_friction")

        burst_window = utc_now() - timedelta(minutes=5)
        burst_attempts = self.db.scalars(
            select(LoginAttempt).where(
                LoginAttempt.user_id == user.id,
                LoginAttempt.organization_id == user.organization_id,
                LoginAttempt.created_at >= burst_window,
            )
        ).all()
        if len(burst_attempts) >= 3:
            risk_score += 0.10
            reasons.append("velocity_detection_triggered")

        if recent_attempts:
            avg_face = sum(float(attempt.face_score or 0) for attempt in recent_attempts) / len(recent_attempts)
            avg_voice = sum(float(attempt.voice_score or 0) for attempt in recent_attempts) / len(recent_attempts)
            if abs(scores.face_score - avg_face) >= 0.18 or abs(scores.voice_score - avg_voice) >= 0.18:
                risk_score += 0.08
                reasons.append("behavior_drift_detected")

        risk_score = self._round_score(max(0.01, min(risk_score, 0.99)))
        risk_level = self._risk_level_from_score(risk_score)
        context_score = self._round_score(max(0.01, 1.0 - risk_score))

        return RiskEvaluation(
            risk_score=risk_score,
            risk_level=risk_level,
            context_score=context_score,
            reasons=reasons,
        )

    def _risk_level_from_score(self, risk_score: float) -> str:
        if risk_score < 0.30:
            return "low"
        if risk_score < 0.55:
            return "medium"
        if risk_score < 0.80:
            return "high"
        return "critical"

    def _round_score(self, value: float) -> float:
        return round(value, 4)
