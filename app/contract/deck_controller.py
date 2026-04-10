from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_deck_service
from app.contract.models.analyze_deck_request import AnalyzeDeckRequest
from app.contract.models.analyze_deck_response import AnalyzeDeckResponse
from app.contract.models.health_response import HealthResponse
from app.domain.service.deck_service import DeckService

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
        "analyze": "/analyze-deck",
    }


@router.post("/analyze-deck", response_model=AnalyzeDeckResponse)
async def analyze_deck(
    request: AnalyzeDeckRequest,
    deck_service: DeckService = Depends(get_deck_service),
) -> AnalyzeDeckResponse:
    try:
        return await deck_service.analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
