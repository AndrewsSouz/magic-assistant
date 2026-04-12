from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_auth_service, get_user_deck_service
from app.contract.models.analyze_deck_response import (
    AnalyzeDeckAcceptedResponse,
)
from app.contract.models.create_user_deck_request import CreateUserDeckRequest
from app.contract.models.create_user_deck_response import CreateUserDeckResponse
from app.contract.models.login_user_request import LoginUserRequest
from app.contract.models.register_user_request import RegisterUserRequest
from app.contract.models.user_deck_response import UserDeckResponse
from app.contract.models.user_response import UserResponse
from app.domain.service.auth_service import AuthService
from app.domain.service.user_deck_service import UserDeckService

router = APIRouter(prefix="/users", tags=["users"])
DECK_RESPONSE_EXCLUDE_FIELDS = {
    "parsed_deck",
    "raw_decklist",
    "enrichment_started_at",
    "enrichment_completed_at",
    "analysis_started_at",
    "analysis_completed_at",
}


def _build_user_deck_response(
    deck,
    user_deck_service: UserDeckService,
) -> UserDeckResponse:
    payload = deck.model_copy(
        update={"cards": user_deck_service.build_response_cards(deck)}
    ).model_dump(exclude=DECK_RESPONSE_EXCLUDE_FIELDS)

    if deck.analysis_result:
        payload["analysis_result"] = {
            **deck.analysis_result.model_dump(),
            "parsed_deck": deck.parsed_deck.model_dump(),
        }

    return UserDeckResponse.model_validate(payload)


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: RegisterUserRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    try:
        user = await auth_service.register(
            email=request.email,
            display_name=request.display_name,
            password=request.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UserResponse.model_validate(user.model_dump())


@router.post("/login", response_model=UserResponse)
async def login_user(
    request: LoginUserRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    user = await auth_service.login(email=request.email, password=request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos.")

    return UserResponse.model_validate(user.model_dump())


@router.post("/{user_id}/decks", response_model=CreateUserDeckResponse)
async def create_user_deck(
    user_id: str,
    request: CreateUserDeckRequest,
    user_deck_service: UserDeckService = Depends(get_user_deck_service),
) -> CreateUserDeckResponse:
    try:
        deck = await user_deck_service.create_deck(
            user_id=user_id,
            name=request.name,
            decklist=request.decklist,
            format_hint=request.format_hint,
            goal=request.goal,
        )
        user_deck_service.schedule_enrichment(user_id, deck.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateUserDeckResponse(
        id=deck.id,
        name=deck.name,
        enrichment_status=deck.enrichment_status,
        message="Deck created successfully. Enrichment started.",
    )


@router.get("/{user_id}/decks", response_model=list[UserDeckResponse])
async def list_user_decks(
    user_id: str,
    user_deck_service: UserDeckService = Depends(get_user_deck_service),
) -> list[UserDeckResponse]:
    try:
        decks = await user_deck_service.list_user_decks(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [
        _build_user_deck_response(deck, user_deck_service)
        for deck in decks
    ]


@router.get("/{user_id}/decks/{deck_id}", response_model=UserDeckResponse)
async def get_user_deck(
    user_id: str,
    deck_id: str,
    user_deck_service: UserDeckService = Depends(get_user_deck_service),
) -> UserDeckResponse:
    try:
        deck = await user_deck_service.get_user_deck(user_id, deck_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _build_user_deck_response(deck, user_deck_service)


@router.post("/{user_id}/decks/{deck_id}/enrich", response_model=CreateUserDeckResponse)
async def retry_enrichment(
    user_id: str,
    deck_id: str,
    user_deck_service: UserDeckService = Depends(get_user_deck_service),
) -> CreateUserDeckResponse:
    try:
        deck = await user_deck_service.retry_enrichment(user_id, deck_id)
        user_deck_service.schedule_enrichment(user_id, deck_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateUserDeckResponse(
        id=deck.id,
        name=deck.name,
        enrichment_status=deck.enrichment_status,
        message="Deck enrichment restarted.",
    )


@router.post(
    "/{user_id}/decks/{deck_id}/analyze",
    response_model=AnalyzeDeckAcceptedResponse,
)
async def analyze_user_deck(
    user_id: str,
    deck_id: str,
    user_deck_service: UserDeckService = Depends(get_user_deck_service),
) -> AnalyzeDeckAcceptedResponse:
    try:
        deck = await user_deck_service.request_analysis(user_id, deck_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AnalyzeDeckAcceptedResponse(
        deck_id=deck.id,
        analysis_status=deck.analysis_status,
        message="Analysis request accepted.",
    )
