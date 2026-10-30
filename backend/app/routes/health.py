"""Health and service information endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Report that the backend process is available."""
    return {"status": "healthy", "service": "DeepGeneLens backend"}
