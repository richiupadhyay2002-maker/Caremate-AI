"""Caremate AI — FastAPI application factory.

Run with::

    uvicorn caremate.api.main:app --reload
    # or with a specific database:
    CAREMATE_DATABASE_URL=sqlite:///caremate_test.db uvicorn caremate.api.main:app --reload
"""

from __future__ import annotations

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from caremate.api.auth.router import router as auth_router
from caremate.api.patients.router import router as patients_router
from caremate.api.documents.router import router as documents_router
from caremate.api.ask.router import router as ask_router
from caremate.api.doctors.router import router as doctors_router
from caremate.api.extras.router import router as extras_router
from contextlib import asynccontextmanager

from caremate.db.config import init_db
from caremate.utils.config import get_logger, get_settings, validate_prod_secrets

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database on startup (idempotent — create_all)."""
    logger.info("Starting Caremate AI API (db=%s)", settings.database_url)
    # In production mode, refuse to boot if required secrets are missing
    validate_prod_secrets()
    init_db()
    # Seed demo accounts for local development; never when production
    # secrets are enforced (the demo passwords are public).
    if settings.force_prod_secrets:
        logger.info("Skipping demo seed (CAREMATE_FORCE_PROD_SECRETS=true)")
        from caremate.scripts.seed import disable_demo_accounts
        disable_demo_accounts()
    else:
        try:
            from caremate.scripts.seed import seed_demo
            seed_demo()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Seed failed: %s", exc)
    yield
    logger.info("Shutting down Caremate AI API")


app = FastAPI(
    title="Caremate AI",
    description="Persistent, patient-isolated medical Q&A service (Phase 2).",
    version="2.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend origin(s) and localhost for development
_origins_env = os.environ.get("CAREMATE_CORS_ORIGINS", "")
if _origins_env:
    origins = _origins_env.split(",")
else:
    origins = [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Security headers — HSTS, X-Content-Type-Options, X-Frame-Options, CSP
# ------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: "Request", call_next):  # noqa: F821
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Allow CDN resources (Swagger UI / ReDoc) on documentation pages;
    # strict CSP everywhere else.
    if request.url.path in ("/docs", "/redoc"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
            "img-src 'self' data: fastapi.tiangoli.com"
        )
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        )
    return response


# Register routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(documents_router)
app.include_router(ask_router)
app.include_router(doctors_router)
app.include_router(extras_router)


@app.get("/health",
         response_model=dict,
         tags=["health"])
async def health() -> dict:
    """Health-check endpoint."""
    return {"status": "ok", "service": "caremate-ai"}


@app.get("/")
async def root() -> dict:
    """Service metadata."""
    return {
        "service": "Caremate AI",
        "version": "2.0.0",
        "phase": "Database & Backend API",
        "docs": "/docs",
    }
