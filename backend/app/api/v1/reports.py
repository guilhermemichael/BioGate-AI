from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.infrastructure.database import get_db
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/attempts.csv")
def export_attempts_csv(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    csv_content = ReportService(db).generate_attempts_csv(current_user)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="biogate-attempts.csv"'},
    )


@router.get("/security-report.pdf")
def export_security_report_pdf(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    pdf_bytes = ReportService(db).generate_security_pdf(current_user)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="biogate-security-report.pdf"'},
    )
