from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_auth_service, get_user_deck_service
from app.contract.models.create_user_deck_request import CreateUserDeckRequest
from app.contract.models.login_user_request import LoginUserRequest
from app.contract.models.register_user_request import RegisterUserRequest
from app.contract.models.user_deck_response import UserDeckResponse
from app.contract.models.user_response import UserResponse
from app.domain.service.auth_service import AuthService
from app.domain.service.user_deck_service import UserDeckService

router = APIRouter(prefix="/users", tags=["users"])


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


@router.post("/{user_id}/decks", response_model=UserDeckResponse)
async def create_user_deck(
    user_id: str,
    request: CreateUserDeckRequest,
    user_deck_service: UserDeckService = Depends(get_user_deck_service),
) -> UserDeckResponse:
    try:
        deck = await user_deck_service.create_deck(
            user_id=user_id,
            name=request.name,
            decklist=request.decklist,
            format_hint=request.format_hint,
            goal=request.goal,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UserDeckResponse.model_validate(deck.model_dump())


@router.get("/{user_id}/decks", response_model=list[UserDeckResponse])
async def list_user_decks(
    user_id: str,
    user_deck_service: UserDeckService = Depends(get_user_deck_service),
) -> list[UserDeckResponse]:
    try:
        decks = await user_deck_service.list_user_decks(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [UserDeckResponse.model_validate(deck.model_dump()) for deck in decks]
