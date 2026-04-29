from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import LoginAttempt, User
from app.schemas.biometric import BiometricAttemptResponse
from app.schemas.dashboard import (
    ConfidenceTrendPoint,
    ConfidenceTrendResponse,
    DashboardRecentAttemptsResponse,
    DashboardSummaryResponse,
    RiskDistributionItem,
    RiskDistributionResponse,
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self, current_user: User) -> DashboardSummaryResponse:
        attempts = self._load_attempts(current_user=current_user, days=None)
        total_attempts = len(attempts)
        counts = Counter(attempt.status for attempt in attempts)
        average_confidence = round(
            sum(float(attempt.final_confidence or 0) for attempt in attempts) / total_attempts,
            4,
        ) if total_attempts else 0.0
        average_risk = round(
            sum(float(attempt.risk_score or 0) for attempt in attempts) / total_attempts,
            4,
        ) if total_attempts else 0.0

        return DashboardSummaryResponse(
            total_attempts=total_attempts,
            approved=counts.get("approved", 0),
            denied=counts.get("denied", 0),
            manual_review=counts.get("manual_review", 0),
            average_confidence=average_confidence,
            average_risk=average_risk,
        )

    def get_recent_attempts(self, current_user: User, limit: int) -> DashboardRecentAttemptsResponse:
        attempts = self._load_attempts(current_user=current_user, days=None, limit=limit)
        return DashboardRecentAttemptsResponse(items=[self._serialize_attempt(attempt) for attempt in attempts])

    def get_risk_distribution(self, current_user: User) -> RiskDistributionResponse:
        attempts = self._load_attempts(current_user=current_user, days=30)
        distribution = Counter((attempt.risk_level or "unknown") for attempt in attempts)
        items = [
            RiskDistributionItem(risk_level=level, count=count)
            for level, count in sorted(distribution.items(), key=lambda item: item[0])
        ]
        return RiskDistributionResponse(items=items)

    def get_confidence_trend(self, current_user: User, days: int = 7) -> ConfidenceTrendResponse:
        attempts = self._load_attempts(current_user=current_user, days=days)
        buckets: dict[date, list[LoginAttempt]] = defaultdict(list)
        for attempt in attempts:
            buckets[attempt.created_at.date()].append(attempt)

        today = date.today()
        points: list[ConfidenceTrendPoint] = []
        for index in range(days - 1, -1, -1):
            day = today - timedelta(days=index)
            day_attempts = buckets.get(day, [])
            total = len(day_attempts)
            avg_confidence = round(
                sum(float(attempt.final_confidence or 0) for attempt in day_attempts) / total,
                4,
            ) if total else 0.0
            avg_risk = round(
                sum(float(attempt.risk_score or 0) for attempt in day_attempts) / total,
                4,
            ) if total else 0.0
            points.append(
                ConfidenceTrendPoint(
                    day=day,
                    average_confidence=avg_confidence,
                    average_risk=avg_risk,
                    total_attempts=total,
                )
            )

        return ConfidenceTrendResponse(items=points)

    def _load_attempts(self, *, current_user: User, days: int | None, limit: int | None = None) -> list[LoginAttempt]:
        filters = [LoginAttempt.final_confidence.is_not(None)]
        if current_user.role != "admin":
            filters.append(LoginAttempt.user_id == current_user.id)
        if days is not None:
            cutoff_date = date.today() - timedelta(days=days - 1)
            cutoff = datetime.combine(cutoff_date, time.min, tzinfo=timezone.utc)
            filters.append(LoginAttempt.created_at >= cutoff)

        query = select(LoginAttempt).where(*filters).order_by(LoginAttempt.created_at.desc())
        if limit is not None:
            query = query.limit(limit)
        return self.db.scalars(query).all()

    def _serialize_attempt(self, attempt: LoginAttempt) -> BiometricAttemptResponse:
        return BiometricAttemptResponse(
            attempt_id=attempt.id,
            user_id=attempt.user_id,
            email_attempted=attempt.email_attempted,
            face_score=float(attempt.face_score) if attempt.face_score is not None else None,
            voice_score=float(attempt.voice_score) if attempt.voice_score is not None else None,
            phrase_score=float(attempt.phrase_score) if attempt.phrase_score is not None else None,
            liveness_score=float(attempt.liveness_score) if attempt.liveness_score is not None else None,
            risk_score=float(attempt.risk_score) if attempt.risk_score is not None else None,
            final_confidence=float(attempt.final_confidence) if attempt.final_confidence is not None else None,
            risk_level=attempt.risk_level,
            status=attempt.status,
            reasons=attempt.decision_reasons_json or [],
            decision_reasons=attempt.decision_reasons_json or [],
            recommended_action=attempt.recommended_action,
            denial_reason=attempt.denial_reason,
            ip_address=attempt.ip_address,
            user_agent=attempt.user_agent,
            device_fingerprint=attempt.device_fingerprint,
            created_at=attempt.created_at,
        )
