"""用户注册、查询与认证业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User

# 用户不存在时也执行一次哈希校验，降低通过响应时间枚举邮箱的可能
_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")


class EmailAlreadyExistsError(Exception):
    """邮箱已被注册。"""


class InvalidCredentialsError(Exception):
    """邮箱或密码错误，或账号已停用。"""


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
) -> User:
    normalized_email = normalize_email(email)
    if await get_user_by_email(session, normalized_email) is not None:
        raise EmailAlreadyExistsError

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise EmailAlreadyExistsError from exc

    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    user = await get_user_by_email(session, email)
    if user is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise InvalidCredentialsError
    if not verify_password(password, user.password_hash) or not user.is_active:
        raise InvalidCredentialsError
    return user
