from dataclasses import dataclass
from decimal import Decimal

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.user import AuditLog, RiskEvent, User


@dataclass(slots=True)
class RequestMetadata:
    ip_address: str | None
    user_agent: str | None
    device_fingerprint: str | None


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def extract_request_metadata(self, request: Request) -> RequestMetadata:
        forwarded_for = request.headers.get("x-forwarded-for")
        ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else None
        if ip_address is None and request.client is not None:
            ip_address = request.client.host

        return RequestMetadata(
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            device_fingerprint=request.headers.get("x-device-fingerprint"),
        )

    def create_audit_log(
        self,
        *,
        action: str,
        severity: str,
        request: Request,
        user: User | None = None,
        entity_name: str | None = None,
        entity_id: str | None = None,
        old_data: dict | None = None,
        new_data: dict | None = None,
    ) -> AuditLog:
        request_metadata = self.extract_request_metadata(request)
        audit_log = AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            severity=severity,
            old_data=old_data,
            new_data=new_data,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
        )
        self.db.add(audit_log)
        return audit_log

    def create_risk_event(
        self,
        *,
        user: User,
        event_type: str,
        risk_level: str,
        score: Decimal | None,
        description: str | None,
        metadata_json: dict | None = None,
    ) -> RiskEvent:
        risk_event = RiskEvent(
            user_id=user.id,
            event_type=event_type,
            risk_level=risk_level,
            score=score,
            description=description,
            metadata_json=metadata_json,
        )
        self.db.add(risk_event)
        return risk_event
