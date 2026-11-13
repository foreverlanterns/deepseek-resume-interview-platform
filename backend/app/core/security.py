"""密码哈希与 JWT 签发/校验。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings

JWT_ALGORITHM = "HS256"
JWT_TYPE = "access"

_password_hash = PasswordHash.recommended()


class InvalidTokenError(Exception):
    """JWT 无效、过期或类型不符。"""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:  # noqa: BLE001 - 损坏的哈希按验证失败处理
        return False


def create_access_token(
    user_id: uuid.UUID,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """返回 (token, 有效期秒数)。"""
    delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + delta,
        "type": JWT_TYPE,
    }
    token = jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )
    return token, int(delta.total_seconds())


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("登录已过期，请重新登录") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("无效的登录凭证") from exc

    if payload.get("type") != JWT_TYPE:
        raise InvalidTokenError("无效的登录凭证")

    subject = payload.get("sub")
    try:
        return uuid.UUID(str(subject))
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("无效的登录凭证") from exc
