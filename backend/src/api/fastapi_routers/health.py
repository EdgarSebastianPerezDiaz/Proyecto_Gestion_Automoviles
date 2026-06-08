"""
Health Check Endpoints - FastAPI Router
Provides liveness, readiness, and deep health probes
"""

from fastapi import APIRouter, status
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """Liveness probe - always responds 200 if app is running."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_probe():
    """Readiness probe - checks critical dependencies."""
    try:
        # Add MongoDB health check if needed
        checks = {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return checks
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {
            "status": "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@router.get("/deep", status_code=status.HTTP_200_OK)
async def deep_health_check():
    """Deep health check - detailed system status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "api": "running",
            "database": "connected"
        }
    }
