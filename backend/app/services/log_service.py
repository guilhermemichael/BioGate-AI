from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.user import AuditLog, LoginAttempt, User
from app.schemas.logs import (
    RelatedAuditEvent,
    SecurityLogDetailResponse,
    SecurityLogItem,
    SecurityLogsListResponse,
)


class LogService:
    def __init__(self, db: Session):
        self.db = db

    def list_logs(
        self,
        *,
        current_user: User,
        limit: int,
        offset: int,
        status_value: str | None,
        risk_level: str | None,
        user_query: str | None,
        ip_address: str | None,
        device: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> SecurityLogsListResponse:
        rows = self._query_attempt_rows(
            current_user=current_user,
            status_value=status_value,
            risk_level=risk_level,
            user_query=user_query,
            ip_address=ip_address,
            device=device,
            date_from=date_from,
            date_to=date_to,
        )
        total = len(rows)
        paginated = rows[offset:offset + limit]
        items = [self._serialize_row(attempt, user) for attempt, user in paginated]
        return SecurityLogsListResponse(total=total, limit=limit, offset=offset, items=items)

    def get_log_detail(self, *, current_user: User, attempt_id: str) -> SecurityLogDetailResponse:
        rows = self._query_attempt_rows(current_user=current_user)
        match = next(((attempt, user) for attempt, user in rows if attempt.id == attempt_id), None)
        if match is None:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Security log was not found.",
            )

        attempt, user = match
        related_events = self.db.scalars(
            select(AuditLog)
            .where(
                AuditLog.organization_id == current_user.organization_id,
                AuditLog.entity_name == "login_attempt",
                AuditLog.entity_id == attempt.id,
            )
            .order_by(AuditLog.created_at.desc())
        ).all()

        return SecurityLogDetailResponse(
            attempt=self._serialize_row(attempt, user),
            related_audit_events=[
                RelatedAuditEvent(
                    id=event.id,
                    organization_id=event.organization_id,
                    action=event.action,
                    severity=event.severity,
                    created_at=event.created_at,
                    ip_address=event.ip_address,
                    user_agent=event.user_agent,
                    request_id=event.request_id,
                    trace_id=event.trace_id,
                    correlation_id=event.correlation_id,
                    previous_hash=event.previous_hash,
                    event_hash=event.event_hash,
                    new_data=event.new_data,
                )
                for event in related_events
            ],
        )

    def _query_attempt_rows(
        self,
        *,
        current_user: User,
        status_value: str | None = None,
        risk_level: str | None = None,
        user_query: str | None = None,
        ip_address: str | None = None,
        device: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[tuple[LoginAttempt, User | None]]:
        query = (
            select(LoginAttempt, User)
            .outerjoin(User, User.id == LoginAttempt.user_id)
            .where(
                LoginAttempt.organization_id == current_user.organization_id,
                LoginAttempt.final_confidence.is_not(None),
            )
            .order_by(LoginAttempt.created_at.desc())
        )

        if current_user.role not in {"admin", "organization_owner", "security_analyst"}:
            query = query.where(LoginAttempt.user_id == current_user.id)
        if status_value:
            query = query.where(LoginAttempt.status == status_value)
        if risk_level:
            query = query.where(LoginAttempt.risk_level == risk_level)
        if user_query:
            pattern = f"%{user_query.lower()}%"
            query = query.where(
                or_(
                    User.email.ilike(pattern),
                    User.full_name.ilike(pattern),
                    LoginAttempt.email_attempted.ilike(pattern),
                )
            )
        if ip_address:
            query = query.where(LoginAttempt.ip_address.ilike(f"%{ip_address}%"))
        if device:
            query = query.where(LoginAttempt.device_fingerprint.ilike(f"%{device}%"))
        if date_from:
            query = query.where(LoginAttempt.created_at >= date_from)
        if date_to:
            query = query.where(LoginAttempt.created_at <= date_to)

        return list(self.db.execute(query).all())

    def _serialize_row(self, attempt: LoginAttempt, user: User | None) -> SecurityLogItem:
        return SecurityLogItem(
            attempt_id=attempt.id,
            organization_id=attempt.organization_id,
            user_id=attempt.user_id,
            user_name=user.full_name if user else None,
            user_email=user.email if user else attempt.email_attempted,
            session_id=attempt.session_id,
            status=attempt.status,
            risk_level=attempt.risk_level,
            context_score=float(attempt.context_score) if attempt.context_score is not None else None,
            face_score=float(attempt.face_score) if attempt.face_score is not None else None,
            voice_score=float(attempt.voice_score) if attempt.voice_score is not None else None,
            phrase_score=float(attempt.phrase_score) if attempt.phrase_score is not None else None,
            liveness_score=float(attempt.liveness_score) if attempt.liveness_score is not None else None,
            risk_score=float(attempt.risk_score) if attempt.risk_score is not None else None,
            final_confidence=float(attempt.final_confidence) if attempt.final_confidence is not None else None,
            ip_address=attempt.ip_address,
            user_agent=attempt.user_agent,
            device_fingerprint=attempt.device_fingerprint,
            reasons=attempt.decision_reasons_json or [],
            risk_reasons=attempt.risk_reasons_json or [],
            score_breakdown=attempt.score_breakdown_json,
            denial_reason=attempt.denial_reason,
            recommended_action=attempt.recommended_action,
            replay_detected=attempt.replay_detected,
            request_id=attempt.request_id,
            trace_id=attempt.trace_id,
            correlation_id=attempt.correlation_id,
            created_at=attempt.created_at,
        )
