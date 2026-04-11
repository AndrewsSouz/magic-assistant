from __future__ import annotations

from app.domain.models.deck.user_deck import UserDeck
from app.integration.deck_repository import DeckRepository
from app.integration.user_repository import UserRepository


class UserDeckService:
    def __init__(
        self,
        user_repository: UserRepository,
        deck_repository: DeckRepository,
    ) -> None:
        self._user_repository = user_repository
        self._deck_repository = deck_repository

    @property
    def enabled(self) -> bool:
        return self._user_repository.enabled and self._deck_repository.enabled

    async def create_deck(
        self,
        user_id: str,
        name: str,
        decklist: str,
        format_hint: str | None,
        goal: str | None,
    ) -> UserDeck:
        if not user_id.strip():
            raise ValueError("user_id é obrigatório.")
        if not name.strip():
            raise ValueError("name é obrigatório.")
        if not decklist.strip():
            raise ValueError("decklist é obrigatório.")

        user = await self._user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado.")

        return await self._deck_repository.create(
            user_id=user_id,
            name=name.strip(),
            decklist=decklist.strip(),
            format_hint=format_hint,
            goal=goal,
        )

    async def list_user_decks(self, user_id: str) -> list[UserDeck]:
        if not user_id.strip():
            raise ValueError("user_id é obrigatório.")
        return await self._deck_repository.list_by_user_id(user_id)
