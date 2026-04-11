from __future__ import annotations

import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

DEFAULT_MONGODB_DATABASE = "magic_assistant"


class MongoIntegration:
    def __init__(self) -> None:
        self._mongo_uri = os.getenv("MONGO_URL")
        self._database_name = os.getenv("MONGO_DATABASE")
        self._client = AsyncIOMotorClient(
            self._mongo_uri) if self._mongo_uri else None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def database(self) -> AsyncIOMotorDatabase:
        if not self._client:
            raise RuntimeError("MongoIntegration is not configured.")
        return self._client[self._database_name]

    async def close(self) -> None:
        if self._client:
            self._client.close()
