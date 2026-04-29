from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(40), default="free", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="organization")
    biometric_profiles: Mapped[list[BiometricProfile]] = relationship(back_populates="organization")
    trusted_devices: Mapped[list[TrustedDevice]] = relationship(back_populates="organization")
    sessions: Mapped[list[UserSession]] = relationship(back_populates="organization")
    login_attempts: Mapped[list[LoginAttempt]] = relationship(back_populates="organization")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="organization")
    risk_events: Mapped[list[RiskEvent]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="users")
    biometric_profile: Mapped[BiometricProfile | None] = relationship(back_populates="user")
    trusted_devices: Mapped[list[TrustedDevice]] = relationship(back_populates="user")
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user")
    login_attempts: Mapped[list[LoginAttempt]] = relationship(back_populates="user")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")
    risk_events: Mapped[list[RiskEvent]] = relationship(back_populates="user")


class BiometricProfile(Base):
    __tablename__ = "biometric_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    face_embedding_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_embedding_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    phrase_secret: Mapped[str | None] = mapped_column(String(280), nullable=True)
    face_model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    voice_model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    consent_version: Mapped[str] = mapped_column(String(40), default="1.0", nullable=False)
    consent_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="biometric_profiles")
    user: Mapped[User] = relationship(back_populates="biometric_profile")


class TrustedDevice(Base):
    __tablename__ = "trusted_devices"
    __table_args__ = (UniqueConstraint("user_id", "fingerprint_hash", name="uq_trusted_devices_user_fingerprint"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fingerprint_preview: Mapped[str | None] = mapped_column(String(120), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="trusted_devices")
    user: Mapped[User] = relationship(back_populates="trusted_devices")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    session_family: Mapped[str] = mapped_column(String(36), nullable=False, default=generate_uuid, index=True)
    rotation_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    device_fingerprint_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    organization: Mapped[Organization] = relationship(back_populates="sessions")
    user: Mapped[User] = relationship(back_populates="sessions")


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    email_attempted: Mapped[str | None] = mapped_column(String(180), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    face_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    voice_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    phrase_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    liveness_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    final_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    denial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_reasons_json: Mapped[list[str] | None] = mapped_column("decision_reasons", JSON, nullable=True)
    risk_reasons_json: Mapped[list[str] | None] = mapped_column("risk_reasons", JSON, nullable=True)
    score_breakdown_json: Mapped[dict | None] = mapped_column("score_breakdown", JSON, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(String(80), nullable=True)
    replay_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    organization: Mapped[Organization | None] = relationship(back_populates="login_attempts")
    user: Mapped[User | None] = relationship(back_populates="login_attempts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    entity_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    severity: Mapped[str] = mapped_column(String(40), default="info", nullable=False)
    old_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    organization: Mapped[Organization | None] = relationship(back_populates="audit_logs")
    user: Mapped[User | None] = relationship(back_populates="audit_logs")


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(40), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    organization: Mapped[Organization] = relationship(back_populates="risk_events")
    user: Mapped[User] = relationship(back_populates="risk_events")
