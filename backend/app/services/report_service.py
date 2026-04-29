import csv
from io import BytesIO, StringIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.dashboard_service import DashboardService
from app.services.log_service import LogService


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.dashboard_service = DashboardService(db)
        self.log_service = LogService(db)

    def generate_attempts_csv(self, current_user: User) -> str:
        logs = self.log_service.list_logs(
            current_user=current_user,
            limit=1000,
            offset=0,
            status_value=None,
            risk_level=None,
            user_query=None,
            ip_address=None,
            device=None,
            date_from=None,
            date_to=None,
        )
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "attempt_id",
                "organization_id",
                "user_name",
                "user_email",
                "status",
                "risk_level",
                "context_score",
                "final_confidence",
                "risk_score",
                "replay_detected",
                "decision_reasons",
                "risk_reasons",
                "ip_address",
                "device_fingerprint",
                "created_at",
            ]
        )
        for item in logs.items:
            writer.writerow(
                [
                    item.attempt_id,
                    item.organization_id,
                    item.user_name,
                    item.user_email,
                    item.status,
                    item.risk_level,
                    item.context_score,
                    item.final_confidence,
                    item.risk_score,
                    item.replay_detected,
                    "|".join(item.reasons),
                    "|".join(item.risk_reasons),
                    item.ip_address,
                    item.device_fingerprint,
                    item.created_at.isoformat(),
                ]
            )
        return buffer.getvalue()

    def generate_security_pdf(self, current_user: User) -> bytes:
        summary = self.dashboard_service.get_summary(current_user)
        recent = self.dashboard_service.get_recent_attempts(current_user, limit=10)

        buffer = BytesIO()
        document = SimpleDocTemplate(buffer, pagesize=A4, title="BioGate AI Security Report")
        styles = getSampleStyleSheet()
        story = [
            Paragraph("BioGate AI Security Report", styles["Title"]),
            Spacer(1, 16),
            Paragraph(f"Organization: {current_user.organization.name}", styles["Heading3"]),
            Spacer(1, 8),
            Paragraph("Executive Summary", styles["Heading2"]),
            Spacer(1, 8),
        ]

        summary_table = Table(
            [
                ["Metric", "Value"],
                ["Total Attempts", summary.total_attempts],
                ["Approved", summary.approved],
                ["Denied", summary.denied],
                ["Manual Review", summary.manual_review],
                ["Average Confidence", summary.average_confidence],
                ["Average Risk", summary.average_risk],
            ]
        )
        summary_table.setStyle(self._table_style())
        story.extend([summary_table, Spacer(1, 16), Paragraph("Recent Attempts", styles["Heading2"]), Spacer(1, 8)])

        attempt_rows = [["Attempt", "Status", "Risk", "Confidence", "Created At"]]
        for item in recent.items:
            attempt_rows.append(
                [
                    item.attempt_id[:8],
                    item.status,
                    item.risk_level or "n/a",
                    item.final_confidence or 0,
                    item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )
        attempts_table = Table(attempt_rows)
        attempts_table.setStyle(self._table_style())
        story.append(attempts_table)

        document.build(story)
        return buffer.getvalue()

    def _table_style(self) -> TableStyle:
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
