from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.domain.models.user.user import User
from app.integration.mongo_integration import MongoIntegration


class UserRepository:
    def __init__(self, mongo_integration: MongoIntegration) -> None:
        self._mongo_integration = mongo_integration

    @property
    def enabled(self) -> bool:
        return self._mongo_integration.enabled

    async def create(
        self,
        email: str,
        display_name: str,
        password_hash: str,
    ) -> User:
        result = await self._collection.insert_one(
            {
                "email": email,
                "display_name": display_name,
                "password_hash": password_hash,
            }
        )
        return User(
            id=str(result.inserted_id),
            email=email,
            display_name=display_name,
        )

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"email": email})

    async def store_password_reset_token(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password_reset_token_hash": token_hash,
                    "password_reset_expires_at": expires_at,
                }
            },
        )

    async def find_by_password_reset_token_hash(
        self,
        token_hash: str,
    ) -> dict[str, Any] | None:
        return await self._collection.find_one(
            {
                "password_reset_token_hash": token_hash,
                "password_reset_expires_at": {"$gt": datetime.now(timezone.utc)},
            }
        )

    async def update_password(
        self,
        user_id: str,
        password_hash: str,
    ) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {"password_hash": password_hash},
                "$unset": {
                    "password_reset_token_hash": "",
                    "password_reset_expires_at": "",
                },
            },
        )

    async def find_by_id(self, user_id: str) -> User | None:
        try:
            object_id = ObjectId(user_id)
        except Exception:
            return None

        document = await self._collection.find_one({"_id": object_id})
        if not document:
            return None
        return self._to_user(document)

    @property
    def _collection(self):
        return self._mongo_integration.database["users"]

    @staticmethod
    def _to_user(document: dict[str, Any]) -> User:
        return User(
            id=str(document["_id"]),
            email=str(document["email"]),
            display_name=str(document["display_name"]),
        )
