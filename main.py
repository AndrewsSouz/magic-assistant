from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.analysis import build_basic_analysis, guess_format
from app.models import AnalyzeDeckRequest, AnalyzeDeckResponse, HealthResponse
from app.parser import parse_decklist
from app.scryfall import CardLookupError, fetch_cards

APP_VERSION = "0.1.0"

app = FastAPI(
    title="Magic Assistant MVP",
    version=APP_VERSION,
    description="Analyze Magic: The Gathering decklists using Scryfall data.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=APP_VERSION)


@app.get("/")
async def root():
    return {
        "service": "magic-assistant-mvp",
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "analyze": "/analyze-deck",
    }


@app.post("/analyze-deck", response_model=AnalyzeDeckResponse)
async def analyze_deck(request: AnalyzeDeckRequest) -> AnalyzeDeckResponse:
    parsed = parse_decklist(request.decklist)

    if not parsed.mainboard:
        raise HTTPException(status_code=400, detail="Decklist inválida ou vazia.")

    try:
        cards = await fetch_cards([item.card_name for item in parsed.mainboard])
    except CardLookupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao consultar Scryfall: {exc}") from exc

    format_guess = request.format_hint or guess_format(parsed)
    result = build_basic_analysis(parsed, cards)

    return AnalyzeDeckResponse(
        format_guess=format_guess,
        summary=result["summary"],
        strengths=result["strengths"],
        weaknesses=result["weaknesses"],
        suggestions=result["suggestions"],
        parsed_deck=parsed,
        card_count=result["card_count"],
        sideboard_count=result["sideboard_count"],
    )
