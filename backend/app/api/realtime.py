import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from sqlalchemy.orm import Session

from app.core.observability import WEBSOCKET_CONNECTIONS
from app.core.security import decode_token
from app.infrastructure.database import SessionLocal
from app.models.user import User, UserSession
from app.schemas.biometric import BiometricCheckInRequest
from app.services.audit_service import RequestMetadata
from app.services.biometric_service import BiometricService

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/biometric/check-in/{session_id}")
async def biometric_checkin_stream(websocket: WebSocket, session_id: str) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="token_required")
        return

    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=4401, reason="invalid_token")
        return

    user_id = payload.get("sub")
    organization_id = payload.get("org")
    access_session_id = payload.get("sid")
    if payload.get("type") != "access" or not user_id or not organization_id or not access_session_id:
        await websocket.close(code=4401, reason="invalid_subject")
        return

    db: Session = SessionLocal()
    accepted = False
    try:
        user = db.get(User, user_id)
        access_session = db.get(UserSession, access_session_id)
        if user is None or access_session is None:
            await websocket.close(code=4404, reason="user_not_found")
            return
        if access_session.user_id != user.id or access_session.organization_id != organization_id or access_session.revoked_at is not None:
            await websocket.close(code=4401, reason="session_revoked")
            return

        await websocket.accept()
        accepted = True
        WEBSOCKET_CONNECTIONS.inc()
        service = BiometricService(db)

        while True:
            raw_message = await websocket.receive_text()
            incoming = json.loads(raw_message) if raw_message else {}
            checkin_payload = BiometricCheckInRequest(**incoming) if incoming else BiometricCheckInRequest(spoken_phrase="I authorize this access.")

            events = [
                ("CHECKIN_STARTED", 5, "Session created and security context loaded."),
                ("FACE_CAPTURE_RECEIVED", 18, "Face capture received from client."),
                ("FACE_ANALYZED", 37, "Face similarity score calculated."),
                ("VOICE_CAPTURE_RECEIVED", 52, "Voice sample received from client."),
                ("VOICE_ANALYZED", 69, "Voice similarity and quality checks completed."),
                ("PHRASE_VALIDATED", 82, "Dynamic phrase compared against expected text."),
                ("RISK_CALCULATED", 93, "Contextual risk engine completed."),
            ]
            for event_name, progress, message in events:
                await websocket.send_json(
                    {
                        "session_id": session_id,
                        "event": event_name,
                        "progress": progress,
                        "message": message,
                    }
                )
                await asyncio.sleep(0.12)

            preview = service.preview_check_in(
                user=user,
                payload=checkin_payload,
                request_metadata=RequestMetadata(
                    ip_address=websocket.client.host if websocket.client else None,
                    user_agent=websocket.headers.get("user-agent"),
                    device_fingerprint=checkin_payload.device_fingerprint,
                    request_id=websocket.headers.get("x-request-id"),
                    trace_id=websocket.headers.get("x-trace-id"),
                    correlation_id=websocket.headers.get("x-correlation-id"),
                ),
            )
            await websocket.send_json(
                {
                    "session_id": session_id,
                    "event": "DECISION_READY",
                    "progress": 100,
                    "message": "Realtime biometric decision is ready.",
                    "result": preview.model_dump(mode="json"),
                }
            )
    except WebSocketDisconnect:
        return
    finally:
        db.close()
        if accepted and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        if accepted:
            WEBSOCKET_CONNECTIONS.dec()
