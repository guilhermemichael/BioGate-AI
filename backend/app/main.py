from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.realtime import router as realtime_router
from app.api.v1.auth import router as auth_router
from app.api.v1.biometric import router as biometric_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.logs import router as logs_router
from app.api.v1.reports import router as reports_router
from app.core.config import get_settings
from app.core.logging import configure_logging, log_json
from app.core.observability import REQUEST_COUNT, REQUEST_LATENCY, render_metrics
from app.infrastructure.database import check_database_connection, init_db

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "BioGate AI backend scaffold for multimodal biometric authentication, "
        "risk scoring, auditability, and security-focused product evolution."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(biometric_router, prefix=settings.api_v1_prefix)
app.include_router(dashboard_router, prefix=settings.api_v1_prefix)
app.include_router(logs_router, prefix=settings.api_v1_prefix)
app.include_router(reports_router, prefix=settings.api_v1_prefix)
app.include_router(realtime_router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    started_at = perf_counter()
    request.state.request_id = request_id
    response = await call_next(request)
    duration = perf_counter() - started_at
    path_template = request.scope.get("route").path if request.scope.get("route") else request.url.path
    REQUEST_COUNT.labels(request.method, path_template, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, path_template).observe(duration)
    response.headers["x-request-id"] = request_id
    log_json(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


@app.get("/", tags=["system"])
async def root() -> dict[str, object]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "version": "0.1.0",
        "status": "online",
        "message": "BioGate AI backend scaffold is running.",
        "modules": [
            "identity-core",
            "biometric-core",
            "risk-engine",
            "decision-engine",
            "audit-engine",
            "behavioral-intelligence",
            "intervention-engine",
        ],
    }


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def readiness() -> dict[str, object]:
    database_ready = check_database_connection()
    return {
        "status": "ready" if database_ready else "degraded",
        "checks": {"database": database_ready},
    }


@app.get("/metrics", tags=["system"])
async def metrics() -> PlainTextResponse:
    payload, content_type = render_metrics()
    return PlainTextResponse(content=payload.decode("utf-8"), media_type=content_type)


@app.get(f"{settings.api_v1_prefix}/overview", tags=["system"])
async def overview() -> dict[str, object]:
    return {
        "product": settings.app_name,
        "positioning": "Biometric Identity and Behavioral Risk Intelligence Platform",
        "mvp_focus": [
            "user registration",
            "password hashing",
            "jwt authentication",
            "protected routes",
            "basic audit logging",
            "demo biometric pipeline",
            "explainable decision engine",
            "dashboard foundation",
            "security logs",
            "realtime websocket",
        ],
        "non_goals": [
            "medical claims",
            "mind reading",
            "absolute emotion detection",
        ],
    }
