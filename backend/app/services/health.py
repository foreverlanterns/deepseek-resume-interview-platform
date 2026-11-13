"""健康检查业务逻辑。"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

FRIENDLY_DATABASE_ERRORS = {
    "InvalidPasswordError": "数据库认证失败，请检查账号或密码",
    "InvalidAuthorizationSpecificationError": "数据库认证失败，请检查账号或密码",
    "InvalidCatalogNameError": "目标数据库不存在，请先创建数据库",
    "ConnectionDoesNotExistError": "数据库连接被关闭，请检查账号、密码及数据库是否存在",
    "ConnectionRefusedError": "无法连接 PostgreSQL，请确认服务已启动",
    "TimeoutError": "数据库连接超时",
}


def describe_database_error(exc: Exception, *, include_detail: bool) -> str:
    """生成不含连接串的错误描述。"""
    friendly = FRIENDLY_DATABASE_ERRORS.get(type(exc).__name__)
    if not include_detail:
        return friendly or type(exc).__name__
    detail = f"{type(exc).__name__}: {exc}"[:300]
    return f"{friendly}（{detail}）" if friendly else detail


async def ping_database(
    session: AsyncSession,
    *,
    include_detail: bool = False,
) -> tuple[bool, str | None]:
    """执行 SELECT 1；失败不抛出，供健康检查返回降级状态。"""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - 健康检查必须兜住所有连接错误
        logger.warning("数据库健康检查失败: %s", type(exc).__name__)
        return False, describe_database_error(exc, include_detail=include_detail)
    return True, None
