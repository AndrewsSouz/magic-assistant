from __future__ import annotations

import hashlib
import hmac
import secrets

from app.domain.models.user.user import User
from app.integration.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    @property
    def enabled(self) -> bool:
        return self._user_repository.enabled

    async def register(self, email: str, display_name: str, password: str) -> User:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("Email é obrigatório.")
        if not password.strip():
            raise ValueError("Senha é obrigatória.")

        existing_user = await self._user_repository.find_by_email(normalized_email)
        if existing_user:
            raise ValueError("Já existe um usuário com esse email.")

        return await self._user_repository.create(
            email=normalized_email,
            display_name=display_name.strip() or normalized_email,
            password_hash=self._hash_password(password),
        )

    async def login(self, email: str, password: str) -> User | None:
        normalized_email = email.strip().lower()
        document = await self._user_repository.find_by_email(normalized_email)
        if not document:
            return None

        if not self._verify_password(password, str(document.get("password_hash") or "")):
            return None

        return User(
            id=str(document["_id"]),
            email=str(document["email"]),
            display_name=str(document["display_name"]),
        )

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()
        return f"{salt}:{digest}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt, expected_digest = stored_hash.split(":", maxsplit=1)
        except ValueError:
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()
        return hmac.compare_digest(actual_digest, expected_digest)
