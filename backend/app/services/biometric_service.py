from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import LoginAttempt, User
from app.schemas.biometric import (
    BiometricAttemptResponse,
    BiometricAttemptsListResponse,
    BiometricCheckInRequest,
)
from app.services.audit_service import AuditService
from app.services.risk_service import RiskService, ScoreBundle

SCORE_PRECISION = Decimal("0.0001")


class BiometricService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.risk_service = RiskService(db)

    def create_check_in(
        self,
        *,
        user: User,
        payload: BiometricCheckInRequest,
        request: Request,
    ) -> BiometricAttemptResponse:
        request_metadata = self.audit_service.extract_request_metadata(request)

        face_score = self._normalize_demo_score(payload.face_capture_quality, floor=0.45)
        voice_score = self._normalize_demo_score(payload.voice_capture_quality, floor=0.45)
        phrase_score = self._score_phrase(payload.spoken_phrase, payload.expected_phrase)
        liveness_score = self._normalize_demo_score(payload.liveness_hint, floor=0.40)

        scores = ScoreBundle(
            face_score=face_score,
            voice_score=voice_score,
            phrase_score=phrase_score,
            liveness_score=liveness_score,
        )
        risk = self.risk_service.evaluate_check_in(
            user=user,
            payload=payload,
            request_metadata=request_metadata,
            scores=scores,
        )

        final_confidence = self._calculate_final_confidence(scores=scores, context_score=risk.context_score, risk_score=risk.risk_score)
        status_value = self._resolve_status(final_confidence)
        recommended_action = self._recommended_action_for_status(status_value)
        reasons = self._build_decision_reasons(scores=scores, risk_level=risk.risk_level, risk_reasons=risk.reasons)
        denial_reason = None if status_value == "approved" else recommended_action

        attempt = LoginAttempt(
            user_id=user.id,
            email_attempted=user.email,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
            device_fingerprint=payload.device_fingerprint or request_metadata.device_fingerprint,
            face_score=self._to_decimal(face_score),
            voice_score=self._to_decimal(voice_score),
            phrase_score=self._to_decimal(phrase_score),
            liveness_score=self._to_decimal(liveness_score),
            risk_score=self._to_decimal(risk.risk_score),
            final_confidence=self._to_decimal(final_confidence),
            risk_level=risk.risk_level,
            status=status_value,
            denial_reason=denial_reason,
            decision_reasons_json=reasons,
            recommended_action=recommended_action,
        )
        self.db.add(attempt)
        self.db.flush()

        severity = "info" if status_value == "approved" else "warning"
        self.audit_service.create_audit_log(
            action="biometric.check_in",
            severity=severity,
            request=request,
            user=user,
            entity_name="login_attempt",
            entity_id=attempt.id,
            new_data={
                "status": status_value,
                "risk_level": risk.risk_level,
                "final_confidence": final_confidence,
                "reasons": reasons,
            },
        )

        if risk.risk_level in {"high", "critical"} or status_value != "approved":
            self.audit_service.create_risk_event(
                user=user,
                event_type="biometric.check_in",
                risk_level=risk.risk_level,
                score=self._to_decimal(risk.risk_score),
                description=f"Biometric demo check-in finished with status {status_value}.",
                metadata_json={
                    "attempt_id": attempt.id,
                    "status": status_value,
                    "reasons": reasons,
                },
            )

        self.db.commit()
        self.db.refresh(attempt)
        return self._serialize_attempt(attempt)

    def list_attempts(
        self,
        *,
        current_user: User,
        limit: int,
        offset: int,
    ) -> BiometricAttemptsListResponse:
        filters = [LoginAttempt.final_confidence.is_not(None)]
        if current_user.role != "admin":
            filters.append(LoginAttempt.user_id == current_user.id)

        total = self.db.scalar(select(func.count()).select_from(LoginAttempt).where(*filters)) or 0
        attempts = self.db.scalars(
            select(LoginAttempt)
            .where(*filters)
            .order_by(LoginAttempt.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return BiometricAttemptsListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[self._serialize_attempt(attempt) for attempt in attempts],
        )

    def get_attempt(self, *, current_user: User, attempt_id: str) -> BiometricAttemptResponse:
        filters = [
            LoginAttempt.id == attempt_id,
            LoginAttempt.final_confidence.is_not(None),
        ]
        if current_user.role != "admin":
            filters.append(LoginAttempt.user_id == current_user.id)

        attempt = self.db.scalar(select(LoginAttempt).where(*filters))
        if attempt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Biometric attempt was not found.",
            )

        return self._serialize_attempt(attempt)

    def _calculate_final_confidence(self, *, scores: ScoreBundle, context_score: float, risk_score: float) -> float:
        weighted_core = (
            (scores.face_score * 0.35)
            + (scores.voice_score * 0.25)
            + (scores.phrase_score * 0.20)
            + (scores.liveness_score * 0.10)
            + (context_score * 0.10)
        )
        risk_penalty = risk_score * 0.05
        return self._normalize_demo_score(weighted_core - risk_penalty, floor=0.01)

    def _resolve_status(self, final_confidence: float) -> str:
        if final_confidence >= 0.85:
            return "approved"
        if final_confidence >= 0.65:
            return "manual_review"
        return "denied"

    def _recommended_action_for_status(self, status_value: str) -> str:
        if status_value == "approved":
            return "grant_access"
        if status_value == "manual_review":
            return "require_additional_verification"
        return "deny_and_retry"

    def _build_decision_reasons(
        self,
        *,
        scores: ScoreBundle,
        risk_level: str,
        risk_reasons: list[str],
    ) -> list[str]:
        reasons: list[str] = []

        if scores.face_score >= 0.90:
            reasons.append("face_match_strong")
        elif scores.face_score >= 0.75:
            reasons.append("face_match_acceptable")
        else:
            reasons.append("face_match_weak")

        if scores.voice_score >= 0.85:
            reasons.append("voice_match_strong")
        elif scores.voice_score >= 0.70:
            reasons.append("voice_match_acceptable")
        else:
            reasons.append("voice_match_weak")

        if scores.phrase_score >= 0.95:
            reasons.append("phrase_verified")
        elif scores.phrase_score >= 0.80:
            reasons.append("phrase_partially_verified")
        else:
            reasons.append("phrase_mismatch_detected")

        if scores.liveness_score >= 0.85:
            reasons.append("liveness_signal_stable")
        else:
            reasons.append("liveness_needs_review")

        reasons.extend(risk_reasons)

        if risk_level == "low":
            reasons.append("risk_low")
        elif risk_level == "medium":
            reasons.append("risk_medium")
        elif risk_level == "high":
            reasons.append("risk_high")
        else:
            reasons.append("risk_critical")

        deduplicated: list[str] = []
        for reason in reasons:
            if reason not in deduplicated:
                deduplicated.append(reason)
        return deduplicated

    def _serialize_attempt(self, attempt: LoginAttempt) -> BiometricAttemptResponse:
        return BiometricAttemptResponse(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            email_attempted=attempt.email_attempted,
            face_score=self._decimal_to_float(attempt.face_score),
            voice_score=self._decimal_to_float(attempt.voice_score),
            phrase_score=self._decimal_to_float(attempt.phrase_score),
            liveness_score=self._decimal_to_float(attempt.liveness_score),
            risk_score=self._decimal_to_float(attempt.risk_score),
            final_confidence=self._decimal_to_float(attempt.final_confidence),
            risk_level=attempt.risk_level,
            status=attempt.status,
            reasons=attempt.decision_reasons_json or [],
            recommended_action=attempt.recommended_action,
            denial_reason=attempt.denial_reason,
            ip_address=attempt.ip_address,
            user_agent=attempt.user_agent,
            device_fingerprint=attempt.device_fingerprint,
            created_at=attempt.created_at,
        )

    def _score_phrase(self, spoken_phrase: str, expected_phrase: str) -> float:
        normalized_spoken = self._normalize_phrase(spoken_phrase)
        normalized_expected = self._normalize_phrase(expected_phrase)

        if normalized_spoken == normalized_expected:
            return 0.96

        similarity = SequenceMatcher(a=normalized_expected, b=normalized_spoken).ratio()
        weighted_similarity = (similarity * 0.92) + 0.04
        return self._normalize_demo_score(weighted_similarity, floor=0.05)

    def _normalize_phrase(self, phrase: str) -> str:
        return " ".join(phrase.lower().split())

    def _normalize_demo_score(self, raw_score: float, *, floor: float) -> float:
        bounded = min(max(raw_score, floor), 0.99)
        return round(bounded, 4)

    def _to_decimal(self, value: float) -> Decimal:
        return Decimal(str(value)).quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)

    def _decimal_to_float(self, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)
