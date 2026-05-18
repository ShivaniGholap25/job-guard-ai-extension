"""routers/health.py — GET /health liveness probe."""

import logging
import time

from fastapi import APIRouter

from core.config import get_settings

logger = APIRouter()
router = APIRouter(tags=["Health"])

_START_TIME = time.time()


@router.get(
    "/health",
    summary="Liveness probe",
    response_description="Service status and metadata",
)
def health_check() -> dict:
    """
    Returns service status, version, and uptime.
    Used by load balancers, monitoring tools, and the Chrome extension
    to verify the backend is reachable before sending analysis requests.
    """
    settings = get_settings()
    return {
        "status":  "ok",
        "version": settings.app_version,
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }
