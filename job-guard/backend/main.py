"""
main.py
-------
Job Guard API — application entry point.

This file is intentionally thin:
  - Creates the FastAPI app
  - Registers middleware
  - Mounts all routers
  - Configures startup / shutdown lifecycle hooks

All business logic lives in services/, all schemas in schemas/,
all route handlers in routers/.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.logging_config import configure_logging

# ── Configure logging before anything else ───────────────────
configure_logging()
logger = logging.getLogger(__name__)

# ── Settings ─────────────────────────────────────────────────
settings = get_settings()

# ── App factory ──────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered Fake Job Offer Detector.\n\n"
        "Combines rule-based signal detection, NLP classification, "
        "scam risk scoring, and phishing URL analysis."
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS middleware ───────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ─────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )

# ── Request logging middleware ────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("→ %s %s", request.method, request.url.path)
    response = await call_next(request)
    logger.info("← %s %s %d", request.method, request.url.path, response.status_code)
    return response

# ── Routers ───────────────────────────────────────────────────
from routers.health       import router as health_router
from routers.analyze      import router as analyze_router
from routers.predict      import router as predict_router
from routers.risk_analysis import router as risk_router
from routers.url_scan     import router as url_router

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(predict_router)
app.include_router(risk_router)
app.include_router(url_router)

# ── Startup / shutdown lifecycle ─────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("=" * 50)
    logger.info("  %s v%s starting up", settings.app_name, settings.app_version)
    logger.info("  Docs: http://localhost:8000/docs")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("%s shutting down", settings.app_name)
