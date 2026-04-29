"""enterprise identity security

Revision ID: 20260429_0002
Revises: 20260429_0001
Create Date: 2026-04-29 06:00:00
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260429_0002"
down_revision = "20260429_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("plan", sa.String(length=40), nullable=False, server_default="free"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_users_organization_id", ["organization_id"], unique=False)

    users = list(bind.execute(sa.text("SELECT id, full_name, email, created_at, updated_at FROM users")))
    for row in users:
        org_id = str(uuid.uuid4())
        slug_root = (row.email.split("@")[0] if row.email else "tenant").lower().replace("_", "-")
        slug = f"legacy-{slug_root}-{row.id[:8]}"
        bind.execute(
            sa.text(
                """
                INSERT INTO organizations (id, name, slug, plan, is_active, created_at, updated_at)
                VALUES (:id, :name, :slug, 'free', 1, :created_at, :updated_at)
                """
            ),
            {
                "id": org_id,
                "name": f"{row.full_name} Workspace",
                "slug": slug[:100],
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            },
        )
        bind.execute(
            sa.text("UPDATE users SET organization_id = :organization_id WHERE id = :user_id"),
            {"organization_id": org_id, "user_id": row.id},
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("organization_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_foreign_key("fk_users_organization_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")

    op.create_table(
        "biometric_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("face_embedding_encrypted", sa.Text(), nullable=True),
        sa.Column("voice_embedding_encrypted", sa.Text(), nullable=True),
        sa.Column("phrase_secret", sa.String(length=280), nullable=True),
        sa.Column("face_model_version", sa.String(length=80), nullable=True),
        sa.Column("voice_model_version", sa.String(length=80), nullable=True),
        sa.Column("consent_version", sa.String(length=40), nullable=False, server_default="1.0"),
        sa.Column("consent_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_biometric_profiles_organization_id", "biometric_profiles", ["organization_id"], unique=False)

    op.create_table(
        "trusted_devices",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("fingerprint_hash", sa.String(length=128), nullable=False),
        sa.Column("fingerprint_preview", sa.String(length=120), nullable=True),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_ip_address", sa.String(length=80), nullable=True),
        sa.Column("last_user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "fingerprint_hash", name="uq_trusted_devices_user_fingerprint"),
    )
    op.create_index("ix_trusted_devices_organization_id", "trusted_devices", ["organization_id"], unique=False)
    op.create_index("ix_trusted_devices_user_id", "trusted_devices", ["user_id"], unique=False)
    op.create_index("ix_trusted_devices_fingerprint_hash", "trusted_devices", ["fingerprint_hash"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("session_family", sa.String(length=36), nullable=False),
        sa.Column("rotation_counter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("device_fingerprint_hash", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_sessions_organization_id", "user_sessions", ["organization_id"], unique=False)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"], unique=False)
    op.create_index("ix_user_sessions_session_family", "user_sessions", ["session_family"], unique=False)
    op.create_index("ix_user_sessions_device_fingerprint_hash", "user_sessions", ["device_fingerprint_hash"], unique=False)

    with op.batch_alter_table("login_attempts") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("session_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("context_score", sa.Numeric(5, 4), nullable=True))
        batch_op.add_column(sa.Column("risk_reasons", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("score_breakdown", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("replay_detected", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("trace_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("correlation_id", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_login_attempts_organization_id", ["organization_id"], unique=False)
        batch_op.create_index("ix_login_attempts_session_id", ["session_id"], unique=False)
        batch_op.create_index("ix_login_attempts_request_id", ["request_id"], unique=False)
        batch_op.create_index("ix_login_attempts_trace_id", ["trace_id"], unique=False)
        batch_op.create_index("ix_login_attempts_correlation_id", ["correlation_id"], unique=False)
        batch_op.create_foreign_key("fk_login_attempts_organization_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
        batch_op.create_foreign_key("fk_login_attempts_session_id", "user_sessions", ["session_id"], ["id"], ondelete="SET NULL")

    bind.execute(
        sa.text(
            """
            UPDATE login_attempts
            SET organization_id = (
                SELECT users.organization_id
                FROM users
                WHERE users.id = login_attempts.user_id
            )
            WHERE user_id IS NOT NULL
            """
        )
    )

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("trace_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("correlation_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("previous_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("event_hash", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_audit_logs_organization_id", ["organization_id"], unique=False)
        batch_op.create_index("ix_audit_logs_request_id", ["request_id"], unique=False)
        batch_op.create_index("ix_audit_logs_trace_id", ["trace_id"], unique=False)
        batch_op.create_index("ix_audit_logs_correlation_id", ["correlation_id"], unique=False)
        batch_op.create_index("ix_audit_logs_event_hash", ["event_hash"], unique=True)
        batch_op.create_foreign_key("fk_audit_logs_organization_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")

    bind.execute(
        sa.text(
            """
            UPDATE audit_logs
            SET organization_id = (
                SELECT users.organization_id
                FROM users
                WHERE users.id = audit_logs.user_id
            )
            WHERE user_id IS NOT NULL
            """
        )
    )

    with op.batch_alter_table("risk_events") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_risk_events_organization_id", ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_risk_events_organization_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")

    bind.execute(
        sa.text(
            """
            UPDATE risk_events
            SET organization_id = (
                SELECT users.organization_id
                FROM users
                WHERE users.id = risk_events.user_id
            )
            WHERE user_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("risk_events") as batch_op:
        batch_op.drop_constraint("fk_risk_events_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_risk_events_organization_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_constraint("fk_audit_logs_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_audit_logs_event_hash")
        batch_op.drop_index("ix_audit_logs_correlation_id")
        batch_op.drop_index("ix_audit_logs_trace_id")
        batch_op.drop_index("ix_audit_logs_request_id")
        batch_op.drop_index("ix_audit_logs_organization_id")
        batch_op.drop_column("event_hash")
        batch_op.drop_column("previous_hash")
        batch_op.drop_column("correlation_id")
        batch_op.drop_column("trace_id")
        batch_op.drop_column("request_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("login_attempts") as batch_op:
        batch_op.drop_constraint("fk_login_attempts_session_id", type_="foreignkey")
        batch_op.drop_constraint("fk_login_attempts_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_login_attempts_correlation_id")
        batch_op.drop_index("ix_login_attempts_trace_id")
        batch_op.drop_index("ix_login_attempts_request_id")
        batch_op.drop_index("ix_login_attempts_session_id")
        batch_op.drop_index("ix_login_attempts_organization_id")
        batch_op.drop_column("correlation_id")
        batch_op.drop_column("trace_id")
        batch_op.drop_column("request_id")
        batch_op.drop_column("replay_detected")
        batch_op.drop_column("score_breakdown")
        batch_op.drop_column("risk_reasons")
        batch_op.drop_column("context_score")
        batch_op.drop_column("session_id")
        batch_op.drop_column("organization_id")

    op.drop_index("ix_user_sessions_device_fingerprint_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_session_family", table_name="user_sessions")
    op.drop_index("ix_user_sessions_refresh_token_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_organization_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_index("ix_trusted_devices_fingerprint_hash", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_user_id", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_organization_id", table_name="trusted_devices")
    op.drop_table("trusted_devices")

    op.drop_index("ix_biometric_profiles_organization_id", table_name="biometric_profiles")
    op.drop_table("biometric_profiles")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_organization_id", type_="foreignkey")
        batch_op.drop_index("ix_users_organization_id")
        batch_op.drop_column("organization_id")

    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
