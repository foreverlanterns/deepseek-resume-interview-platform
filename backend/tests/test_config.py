"""配置系统测试：PostgreSQL 约束、脱敏、生产安全校验。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings

VALID_DB = "postgresql+asyncpg://resume_app:secret@127.0.0.1:5432/resume_platform"


def build_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_postgres_scheme_is_normalized_to_asyncpg() -> None:
    settings = build_settings(database_url="postgresql://u:p@localhost:5432/db")
    assert settings.database_url == "postgresql+asyncpg://u:p@localhost:5432/db"


def test_legacy_postgres_scheme_is_normalized() -> None:
    settings = build_settings(database_url="postgres://u:p@localhost:5432/db")
    assert settings.database_url == "postgresql+asyncpg://u:p@localhost:5432/db"


def test_psycopg_url_is_normalized_for_application() -> None:
    settings = build_settings(database_url="postgresql+psycopg://u:p@localhost:5432/db")
    assert settings.database_url == "postgresql+asyncpg://u:p@localhost:5432/db"


def test_sync_database_url_uses_psycopg_for_alembic() -> None:
    settings = build_settings(database_url=VALID_DB)
    assert settings.sync_database_url == (
        "postgresql+psycopg://resume_app:secret@127.0.0.1:5432/resume_platform"
    )


def test_test_database_url_can_be_empty() -> None:
    assert build_settings(test_database_url="").test_database_url == ""


def test_test_database_url_is_normalized() -> None:
    settings = build_settings(test_database_url="postgresql://u:p@localhost:5432/db_test")
    assert settings.test_database_url == "postgresql+asyncpg://u:p@localhost:5432/db_test"


def test_test_database_url_rejects_sqlite() -> None:
    with pytest.raises(ValidationError):
        build_settings(test_database_url="sqlite:///./test.db")


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///./app.db",
        "sqlite+aiosqlite:///./app.db",
        "mysql://u:p@localhost/db",
        "",
    ],
)
def test_non_postgres_url_is_rejected(url: str) -> None:
    with pytest.raises(ValidationError):
        build_settings(database_url=url)


def test_database_url_safe_hides_credentials() -> None:
    settings = build_settings(database_url=VALID_DB)
    safe = settings.database_url_safe
    assert "secret" not in safe
    assert "resume_app" not in safe
    assert safe == "postgresql+asyncpg://127.0.0.1:5432/resume_platform"


def test_cors_origins_accept_comma_separated_values() -> None:
    settings = build_settings(cors_origins="http://a.test, http://b.test ,")
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_log_level_is_normalized_and_validated() -> None:
    assert build_settings(log_level="debug").log_level == "DEBUG"
    with pytest.raises(ValidationError):
        build_settings(log_level="VERBOSE")


def test_production_requires_non_debug_mode() -> None:
    with pytest.raises(ValidationError):
        build_settings(
            environment="production",
            debug=True,
            secret_key="a" * 32,
            database_url=VALID_DB,
        )


def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValidationError):
        build_settings(
            environment="production",
            debug=False,
            secret_key=DEFAULT_SECRET_KEY,
            database_url=VALID_DB,
        )


def test_production_accepts_strong_secret() -> None:
    settings = build_settings(
        environment="production",
        debug=False,
        secret_key="b" * 64,
        database_url=VALID_DB,
    )
    assert settings.is_production is True
