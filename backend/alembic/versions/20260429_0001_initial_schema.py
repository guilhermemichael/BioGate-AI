"""initial schema

Revision ID: 20260429_0001
Revises:
Create Date: 2026-04-29 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260429_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="user"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("email_attempted", sa.String(length=180), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("device_fingerprint", sa.Text(), nullable=True),
        sa.Column("face_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("voice_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("phrase_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("liveness_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("risk_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("final_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("risk_level", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("denial_reason", sa.Text(), nullable=True),
        sa.Column("decision_reasons", sa.JSON(), nullable=True),
        sa.Column("recommended_action", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_login_attempts_user_id", "login_attempts", ["user_id"], unique=False)
    op.create_index("ix_login_attempts_created_at", "login_attempts", ["created_at"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_name", sa.String(length=120), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("severity", sa.String(length=40), nullable=False, server_default="info"),
        sa.Column("old_data", sa.JSON(), nullable=True),
        sa.Column("new_data", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)

    op.create_table(
        "risk_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_risk_events_user_id", "risk_events", ["user_id"], unique=False)
    op.create_index("ix_risk_events_created_at", "risk_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_risk_events_created_at", table_name="risk_events")
    op.drop_index("ix_risk_events_user_id", table_name="risk_events")
    op.drop_table("risk_events")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_login_attempts_created_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_user_id", table_name="login_attempts")
    op.drop_table("login_attempts")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
