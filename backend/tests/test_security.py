"""密码哈希与 JWT 单元测试。"""

from __future__ import annotations

import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    JWT_ALGORITHM,
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    hashed = hash_password("StrongPass123")

    assert hashed.startswith("$argon2")
    assert hashed != "StrongPass123"
    assert verify_password("StrongPass123", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_handles_broken_hash() -> None:
    assert verify_password("anything", "not-a-valid-hash") is False


def test_access_token_round_trip(settings: Settings) -> None:
    user_id = uuid.uuid4()

    token, expires_in = create_access_token(user_id, settings)

    assert expires_in == settings.access_token_expire_minutes * 60
    assert decode_access_token(token, settings) == user_id


def test_expired_token_is_rejected(settings: Settings) -> None:
    token, _ = create_access_token(uuid.uuid4(), settings, timedelta(seconds=-1))

    with pytest.raises(InvalidTokenError, match="登录已过期"):
        decode_access_token(token, settings)


def test_malformed_token_is_rejected(settings: Settings) -> None:
    with pytest.raises(InvalidTokenError, match="无效的登录凭证"):
        decode_access_token("not-a-jwt", settings)


def test_token_signed_with_other_key_is_rejected(settings: Settings) -> None:
    other_settings = Settings(
        _env_file=None,
        secret_key="another-secret-key-with-at-least-32-characters",
    )
    token, _ = create_access_token(uuid.uuid4(), other_settings)

    with pytest.raises(InvalidTokenError, match="无效的登录凭证"):
        decode_access_token(token, settings)


def test_non_access_token_is_rejected(settings: Settings) -> None:
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "refresh"},
        settings.secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )

    with pytest.raises(InvalidTokenError, match="无效的登录凭证"):
        decode_access_token(token, settings)
