from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.domain.models.deck.user_deck import UserDeck
from app.integration.mongo_integration import MongoIntegration


class DeckRepository:
    def __init__(self, mongo_integration: MongoIntegration) -> None:
        self._mongo_integration = mongo_integration

    @property
    def enabled(self) -> bool:
        return self._mongo_integration.enabled

    async def create(
        self,
        user_id: str,
        name: str,
        decklist: str,
        format_hint: str | None,
        goal: str | None,
    ) -> UserDeck:
        result = await self._collection.insert_one(
            {
                "user_id": user_id,
                "name": name,
                "decklist": decklist,
                "format_hint": format_hint,
                "goal": goal,
            }
        )
        return UserDeck(
            id=str(result.inserted_id),
            user_id=user_id,
            name=name,
            decklist=decklist,
            format_hint=format_hint,
            goal=goal,
        )

    async def list_by_user_id(self, user_id: str) -> list[UserDeck]:
        cursor = self._collection.find({"user_id": user_id}).sort("_id", -1)
        documents = await cursor.to_list(length=100)
        return [self._to_user_deck(document) for document in documents]

    async def find_by_id_and_user_id(self, deck_id: str, user_id: str) -> UserDeck | None:
        try:
            object_id = ObjectId(deck_id)
        except Exception:
            return None

        document = await self._collection.find_one({"_id": object_id, "user_id": user_id})
        if not document:
            return None
        return self._to_user_deck(document)

    @property
    def _collection(self):
        return self._mongo_integration.database["decks"]

    @staticmethod
    def _to_user_deck(document: dict[str, Any]) -> UserDeck:
        return UserDeck(
            id=str(document["_id"]),
            user_id=str(document["user_id"]),
            name=str(document["name"]),
            decklist=str(document["decklist"]),
            format_hint=document.get("format_hint"),
            goal=document.get("goal"),
        )
