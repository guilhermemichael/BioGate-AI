from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.core.config import get_settings
from app.infrastructure.database import init_db

settings = get_settings()


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
            "audit-engine",
            "behavioral-intelligence",
            "intervention-engine",
        ],
    }


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


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
            "risk scoring",
            "dashboard foundation",
        ],
        "non_goals": [
            "medical claims",
            "mind reading",
            "absolute emotion detection",
        ],
    }
