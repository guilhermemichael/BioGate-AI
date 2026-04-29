from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_secret, utc_now
from app.models.user import TrustedDevice, User
from app.services.audit_service import RequestMetadata


@dataclass(slots=True)
class DeviceAssessment:
    raw_fingerprint: str | None
    fingerprint_hash: str | None
    trusted_device: TrustedDevice | None
    is_known: bool
    is_trusted: bool


class DeviceService:
    def __init__(self, db: Session):
        self.db = db

    def assess_device(
        self,
        *,
        user: User,
        raw_fingerprint: str | None,
    ) -> DeviceAssessment:
        normalized = self._normalize_fingerprint(raw_fingerprint)
        if normalized is None:
            return DeviceAssessment(
                raw_fingerprint=None,
                fingerprint_hash=None,
                trusted_device=None,
                is_known=False,
                is_trusted=False,
            )

        fingerprint_hash = hash_secret(normalized)
        trusted_device = self.db.scalar(
            select(TrustedDevice).where(
                TrustedDevice.user_id == user.id,
                TrustedDevice.fingerprint_hash == fingerprint_hash,
            )
        )
        return DeviceAssessment(
            raw_fingerprint=normalized,
            fingerprint_hash=fingerprint_hash,
            trusted_device=trusted_device,
            is_known=trusted_device is not None,
            is_trusted=bool(trusted_device and trusted_device.is_trusted),
        )

    def register_device_event(
        self,
        *,
        user: User,
        request_metadata: RequestMetadata,
        raw_fingerprint: str | None,
        trust_device: bool,
    ) -> TrustedDevice | None:
        assessment = self.assess_device(user=user, raw_fingerprint=raw_fingerprint)
        if assessment.fingerprint_hash is None:
            return None

        device = assessment.trusted_device
        if device is None:
            device = TrustedDevice(
                organization_id=user.organization_id,
                user_id=user.id,
                fingerprint_hash=assessment.fingerprint_hash,
                fingerprint_preview=self._preview_fingerprint(assessment.raw_fingerprint),
                display_name=self._derive_display_name(request_metadata.user_agent),
                is_trusted=trust_device,
                first_seen_at=utc_now(),
                last_seen_at=utc_now(),
                last_ip_address=request_metadata.ip_address,
                last_user_agent=request_metadata.user_agent,
            )
            self.db.add(device)
            return device

        device.last_seen_at = utc_now()
        device.last_ip_address = request_metadata.ip_address
        device.last_user_agent = request_metadata.user_agent
        if trust_device:
            device.is_trusted = True
        return device

    def list_devices(self, *, user: User) -> list[TrustedDevice]:
        return list(
            self.db.scalars(
                select(TrustedDevice)
                .where(TrustedDevice.user_id == user.id)
                .order_by(TrustedDevice.last_seen_at.desc())
            ).all()
        )

    def revoke_device(self, *, user: User, device_id: str) -> TrustedDevice | None:
        device = self.db.scalar(
            select(TrustedDevice).where(
                TrustedDevice.id == device_id,
                TrustedDevice.user_id == user.id,
            )
        )
        if device is None:
            return None
        device.is_trusted = False
        device.last_seen_at = utc_now()
        return device

    def _normalize_fingerprint(self, raw_fingerprint: str | None) -> str | None:
        if raw_fingerprint is None:
            return None
        normalized = raw_fingerprint.strip()
        return normalized or None

    def _preview_fingerprint(self, raw_fingerprint: str | None) -> str | None:
        if raw_fingerprint is None:
            return None
        return raw_fingerprint[:120]

    def _derive_display_name(self, user_agent: str | None) -> str:
        if not user_agent:
            return "Unknown device"
        return user_agent[:160]
