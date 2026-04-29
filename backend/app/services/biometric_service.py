from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.decision import DecisionInput
from app.models.user import LoginAttempt, User
from app.schemas.biometric import (
    BiometricAttemptResponse,
    BiometricAttemptsListResponse,
    BiometricCheckInRequest,
)
from app.services.audit_service import AuditService, RequestMetadata
from app.services.decision_service import DecisionService
from app.services.risk_service import RiskService, ScoreBundle

SCORE_PRECISION = Decimal("0.0001")


class BiometricService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.risk_service = RiskService(db)
        self.decision_service = DecisionService()

    def create_check_in(
        self,
        *,
        user: User,
        payload: BiometricCheckInRequest,
        request: Request,
    ) -> BiometricAttemptResponse:
        request_metadata = self.audit_service.extract_request_metadata(request)
        preview = self.preview_check_in(user=user, payload=payload, request_metadata=request_metadata)

        attempt = LoginAttempt(
            user_id=user.id,
            email_attempted=user.email,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
            device_fingerprint=payload.device_fingerprint or request_metadata.device_fingerprint,
            face_score=self._to_decimal(preview.face_score or 0),
            voice_score=self._to_decimal(preview.voice_score or 0),
            phrase_score=self._to_decimal(preview.phrase_score or 0),
            liveness_score=self._to_decimal(preview.liveness_score or 0),
            risk_score=self._to_decimal(preview.risk_score or 0),
            final_confidence=self._to_decimal(preview.final_confidence or 0),
            risk_level=preview.risk_level,
            status=preview.status,
            denial_reason=preview.denial_reason,
            decision_reasons_json=preview.decision_reasons,
            recommended_action=preview.recommended_action,
        )
        self.db.add(attempt)
        self.db.flush()

        severity = "info" if preview.status == "approved" else "warning"
        self.audit_service.create_audit_log(
            action="biometric.check_in",
            severity=severity,
            request=request,
            user=user,
            entity_name="login_attempt",
            entity_id=attempt.id,
            new_data={
                "status": preview.status,
                "risk_level": preview.risk_level,
                "final_confidence": preview.final_confidence,
                "reasons": preview.decision_reasons,
            },
        )

        if (preview.risk_level or "low") in {"high", "critical"} or preview.status != "approved":
            self.audit_service.create_risk_event(
                user=user,
                event_type="biometric.check_in",
                risk_level=preview.risk_level or "low",
                score=self._to_decimal(preview.risk_score or 0),
                description=f"Biometric demo check-in finished with status {preview.status}.",
                metadata_json={
                    "attempt_id": attempt.id,
                    "status": preview.status,
                    "reasons": preview.decision_reasons,
                },
            )

        self.db.commit()
        self.db.refresh(attempt)
        return self._serialize_attempt(attempt)

    def preview_check_in(
        self,
        *,
        user: User,
        payload: BiometricCheckInRequest,
        request_metadata: RequestMetadata,
    ) -> BiometricAttemptResponse:
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
        decision = self.decision_service.evaluate(
            DecisionInput(
                face_score=face_score,
                voice_score=voice_score,
                phrase_score=phrase_score,
                liveness_score=liveness_score,
                context_score=risk.context_score,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                risk_reasons=risk.reasons,
            )
        )
        denial_reason = None if decision.status == "approved" else decision.recommended_action

        return BiometricAttemptResponse(
            attempt_id="preview",
            user_id=user.id,
            email_attempted=user.email,
            face_score=face_score,
            voice_score=voice_score,
            phrase_score=phrase_score,
            liveness_score=liveness_score,
            risk_score=risk.risk_score,
            final_confidence=decision.final_confidence,
            risk_level=risk.risk_level,
            status=decision.status,
            reasons=decision.decision_reasons,
            decision_reasons=decision.decision_reasons,
            recommended_action=decision.recommended_action,
            denial_reason=denial_reason,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
            device_fingerprint=payload.device_fingerprint or request_metadata.device_fingerprint,
            created_at=datetime.now(timezone.utc),
        )

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

    def _serialize_attempt(self, attempt: LoginAttempt) -> BiometricAttemptResponse:
        decision_reasons = attempt.decision_reasons_json or []
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
            reasons=decision_reasons,
            decision_reasons=decision_reasons,
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
