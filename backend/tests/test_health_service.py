"""健康检查错误描述测试。"""

from __future__ import annotations

from app.services.health import describe_database_error, ping_database


class InvalidPasswordError(Exception):
    """模拟 asyncpg 认证失败异常类型。"""


class ConnectionRefusedError(Exception):
    """模拟端口不可达异常类型。"""


def test_known_error_maps_to_chinese_hint() -> None:
    message = describe_database_error(InvalidPasswordError("auth failed"), include_detail=False)
    assert message == "数据库认证失败，请检查账号或密码"


def test_known_error_keeps_raw_detail_in_debug() -> None:
    message = describe_database_error(ConnectionRefusedError("refused"), include_detail=True)
    assert message.startswith("无法连接 PostgreSQL")
    assert "ConnectionRefusedError: refused" in message


def test_unknown_error_falls_back_to_type_name() -> None:
    class WeirdError(Exception):
        pass

    assert describe_database_error(WeirdError("x"), include_detail=False) == "WeirdError"


async def test_ping_database_returns_false_on_error() -> None:
    class BrokenSession:
        async def execute(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError("boom")

    ok, error = await ping_database(BrokenSession(), include_detail=False)  # type: ignore[arg-type]
    assert ok is False
    assert error == "RuntimeError"
