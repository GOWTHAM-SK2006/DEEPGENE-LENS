"""FastAPI application entry point for DeepGeneLens."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.health import router as health_router
from app.routes.uploads import router as uploads_router
from app.routes.predict import router as predict_router

settings = get_settings()

app = FastAPI(
    title=settings["app_name"],
    description="Research-prototype API foundation for AI-powered genomic analysis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["frontend_origins"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(uploads_router, prefix="/api/uploads")
app.include_router(predict_router, prefix="/api/analysis")


@app.get("/", tags=["system"])
def welcome() -> dict[str, str]:
    """Return the project welcome message."""
    return {
        "message": "Welcome to DeepGeneLens",
        "description": "AI Genomic Analysis Platform research prototype",
    }
