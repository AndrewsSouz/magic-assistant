import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.analysis import build_basic_analysis, guess_format
from app.logging_config import configure_logging
from app.models import AnalyzeDeckRequest, AnalyzeDeckResponse, HealthResponse
from app.parser import parse_decklist
from app.scryfall import CardLookupError, fetch_cards

APP_VERSION = "0.1.0"
log_file = configure_logging()
log = logging.getLogger(__name__)

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


@app.on_event("startup")
async def startup_event() -> None:
    log.info("Application started. Logs are being written to %s", log_file)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Unhandled error while processing %s %s", request.method, request.url.path)
        raise

    if response.status_code >= 400:
        log.warning("HTTP %s %s -> %s", request.method, request.url.path, response.status_code)

    return response


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
        log.warning("Analyze request rejected: empty or invalid decklist")
        raise HTTPException(status_code=400, detail="Decklist inválida ou vazia.")

    try:
        cards = await fetch_cards([item.card_name for item in parsed.mainboard])
    except CardLookupError as exc:
        log.warning("Card lookup failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Unexpected card provider error")
        raise HTTPException(status_code=502, detail=f"Erro ao consultar provedores de cartas: {exc}") from exc

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
