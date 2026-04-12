from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.domain.models.deck.deck_analysis import DeckAnalysis
from app.domain.models.deck.user_deck import UserDeck
from app.integration.mongo_integration import MongoIntegration


class DeckRepository:
    def __init__(self, mongo_integration: MongoIntegration) -> None:
        self._mongo_integration = mongo_integration

    @property
    def enabled(self) -> bool:
        return self._mongo_integration.enabled

    async def create(self, deck: UserDeck) -> UserDeck:
        payload = deck.model_dump(mode="json")
        payload.pop("id", None)
        result = await self._collection.insert_one(payload)
        return deck.model_copy(update={"id": str(result.inserted_id)})

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

    async def mark_enrichment_processing(self, deck_id: str) -> None:
        await self._update_deck(
            deck_id,
            {
                "enrichment_status": "processing",
                "enrichment_error": None,
                "enrichment_started_at": self._utcnow(),
                "updated_at": self._utcnow(),
            },
        )

    async def complete_enrichment(
        self,
        deck_id: str,
        *,
        cards: list[dict[str, Any]],
        format_guess: str,
        card_count: int,
        sideboard_count: int,
    ) -> None:
        await self._update_deck(
            deck_id,
            {
                "cards": cards,
                "format_guess": format_guess,
                "card_count": card_count,
                "sideboard_count": sideboard_count,
                "enrichment_status": "completed",
                "enrichment_error": None,
                "enrichment_completed_at": self._utcnow(),
                "updated_at": self._utcnow(),
            },
        )

    async def mark_enrichment_pending(self, deck_id: str, error: str) -> None:
        await self._update_deck(
            deck_id,
            {
                "enrichment_status": "pending",
                "enrichment_error": error,
                "enrichment_completed_at": None,
                "updated_at": self._utcnow(),
            },
        )

    async def fail_enrichment(self, deck_id: str, error: str) -> None:
        await self._update_deck(
            deck_id,
            {
                "enrichment_status": "failed",
                "enrichment_error": error,
                "enrichment_completed_at": self._utcnow(),
                "updated_at": self._utcnow(),
            },
        )

    async def reset_enrichment(self, deck_id: str) -> None:
        await self._update_deck(
            deck_id,
            {
                "cards": [],
                "format_guess": None,
                "card_count": 0,
                "sideboard_count": 0,
                "enrichment_status": "pending",
                "enrichment_error": None,
                "enrichment_started_at": None,
                "enrichment_completed_at": None,
                "updated_at": self._utcnow(),
            },
        )

    async def mark_analysis_pending(self, deck_id: str) -> None:
        now = self._utcnow()
        await self._update_deck(
            deck_id,
            {
                "analysis_status": "pending",
                "analysis_error": None,
                "analysis_started_at": now,
                "analysis_completed_at": None,
                "analysis_result": None,
                "updated_at": now,
            },
        )

    async def complete_analysis(self, deck_id: str, analysis_result: DeckAnalysis) -> None:
        now = self._utcnow()
        await self._update_deck(
            deck_id,
            {
                "analysis_status": "done",
                "analysis_error": None,
                "analysis_completed_at": now,
                "analysis_result": analysis_result.model_dump(mode="json"),
                "updated_at": now,
            },
        )

    async def fail_analysis(self, deck_id: str, error: str) -> None:
        now = self._utcnow()
        await self._update_deck(
            deck_id,
            {
                "analysis_status": "failed",
                "analysis_error": error,
                "analysis_completed_at": now,
                "updated_at": now,
            },
        )

    async def _update_deck(self, deck_id: str, fields: dict[str, Any]) -> None:
        object_id = ObjectId(deck_id)
        await self._collection.update_one({"_id": object_id}, {"$set": fields})

    @property
    def _collection(self):
        return self._mongo_integration.database["decks"]

    @staticmethod
    def _to_user_deck(document: dict[str, Any]) -> UserDeck:
        return UserDeck(
            id=str(document["_id"]),
            user_id=str(document["user_id"]),
            name=str(document["name"]),
            raw_decklist=str(document["raw_decklist"]),
            parsed_deck=document.get("parsed_deck") or {"mainboard": [], "sideboard": []},
            cards=document.get("cards") or [],
            format_guess=document.get("format_guess"),
            card_count=int(document.get("card_count") or 0),
            sideboard_count=int(document.get("sideboard_count") or 0),
            enrichment_status=str(document.get("enrichment_status") or "pending"),
            enrichment_error=document.get("enrichment_error"),
            enrichment_started_at=document.get("enrichment_started_at"),
            enrichment_completed_at=document.get("enrichment_completed_at"),
            analysis_status=str(document.get("analysis_status") or "not_requested"),
            analysis_error=document.get("analysis_error"),
            analysis_started_at=document.get("analysis_started_at"),
            analysis_completed_at=document.get("analysis_completed_at"),
            analysis_result=document.get("analysis_result"),
            created_at=document.get("created_at") or DeckRepository._utcnow(),
            updated_at=document.get("updated_at") or DeckRepository._utcnow(),
            format_hint=document.get("format_hint"),
            goal=document.get("goal"),
        )

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)
