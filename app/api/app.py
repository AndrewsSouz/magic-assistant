from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.contract.deck_controller import router as deck_router
from app.contract.user_deck_controller import router as user_deck_router
from app.config.logging_config import configure_logging

APP_VERSION = "0.1.0"

log_file = configure_logging()
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
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

    app.include_router(deck_router)
    app.include_router(user_deck_router)

    return app
