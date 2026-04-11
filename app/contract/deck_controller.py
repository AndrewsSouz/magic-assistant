from __future__ import annotations

from fastapi import APIRouter

from app.contract.models.health_response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/")
async def root():
    return {
        "service": "magic-assistant-mvp",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "users": "/users",
    }
