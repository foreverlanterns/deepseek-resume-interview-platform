"""API 依赖：数据库会话、配置与当前登录用户。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.providers.base import JsonCompletionProvider
from app.providers.deepseek import DeepSeekProvider

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_app_settings(request: Request) -> Settings:
    """从应用实例读取配置，保证 create_app(settings) 注入生效。"""
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_app_settings)]


def get_json_provider(settings: AppSettings) -> JsonCompletionProvider:
    return DeepSeekProvider(settings)


JsonProviderDep = Annotated[JsonCompletionProvider, Depends(get_json_provider)]

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "请先登录") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: DbSession,
    settings: AppSettings,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except InvalidTokenError as exc:
        raise _unauthorized(str(exc)) from exc

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("账号不存在或已停用")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
