from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import AuditLog, Organization, RiskEvent, User


@dataclass(slots=True)
class RequestMetadata:
    ip_address: str | None
    user_agent: str | None
    device_fingerprint: str | None
    request_id: str | None
    trace_id: str | None
    correlation_id: str | None


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def extract_request_metadata(self, request: Request) -> RequestMetadata:
        forwarded_for = request.headers.get("x-forwarded-for")
        ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else None
        if ip_address is None and request.client is not None:
            ip_address = request.client.host

        request_id = getattr(request.state, "request_id", None) or request.headers.get("x-request-id")
        trace_id = request.headers.get("x-trace-id") or request_id
        correlation_id = request.headers.get("x-correlation-id") or request_id

        return RequestMetadata(
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
            device_fingerprint=request.headers.get("x-device-fingerprint"),
            request_id=request_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

    def create_audit_log(
        self,
        *,
        action: str,
        severity: str,
        request: Request,
        user: User | None = None,
        organization: Organization | None = None,
        entity_name: str | None = None,
        entity_id: str | None = None,
        old_data: dict | None = None,
        new_data: dict | None = None,
    ) -> AuditLog:
        request_metadata = self.extract_request_metadata(request)
        organization_id = (
            organization.id
            if organization is not None
            else user.organization_id
            if user is not None
            else None
        )
        previous_hash = self.db.scalar(
            select(AuditLog.event_hash)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        event_hash = self._build_event_hash(
            previous_hash=previous_hash,
            action=action,
            severity=severity,
            user_id=user.id if user else None,
            organization_id=organization_id,
            entity_name=entity_name,
            entity_id=entity_id,
            old_data=old_data,
            new_data=new_data,
            request_metadata=request_metadata,
        )

        audit_log = AuditLog(
            organization_id=organization_id,
            user_id=user.id if user else None,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            severity=severity,
            old_data=old_data,
            new_data=new_data,
            ip_address=request_metadata.ip_address,
            user_agent=request_metadata.user_agent,
            request_id=request_metadata.request_id,
            trace_id=request_metadata.trace_id,
            correlation_id=request_metadata.correlation_id,
            previous_hash=previous_hash,
            event_hash=event_hash,
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
            organization_id=user.organization_id,
            user_id=user.id,
            event_type=event_type,
            risk_level=risk_level,
            score=score,
            description=description,
            metadata_json=metadata_json,
        )
        self.db.add(risk_event)
        return risk_event

    def _build_event_hash(
        self,
        *,
        previous_hash: str | None,
        action: str,
        severity: str,
        user_id: str | None,
        organization_id: str | None,
        entity_name: str | None,
        entity_id: str | None,
        old_data: dict | None,
        new_data: dict | None,
        request_metadata: RequestMetadata,
    ) -> str:
        serialized = json.dumps(
            {
                "previous_hash": previous_hash,
                "action": action,
                "severity": severity,
                "user_id": user_id,
                "organization_id": organization_id,
                "entity_name": entity_name,
                "entity_id": entity_id,
                "old_data": old_data,
                "new_data": new_data,
                "ip_address": request_metadata.ip_address,
                "request_id": request_metadata.request_id,
                "trace_id": request_metadata.trace_id,
                "correlation_id": request_metadata.correlation_id,
            },
            sort_keys=True,
            default=str,
        )
        return sha256(serialized.encode("utf-8")).hexdigest()
