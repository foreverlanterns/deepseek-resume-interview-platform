"""应用配置：全部来自环境变量或 backend/.env，业务代码不写死密钥与模型名。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SECRET_KEY = "dev-only-change-me"
ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


def normalize_postgres_url(value: object, *, field_name: str) -> str:
    """把 PostgreSQL 连接串归一为 asyncpg 驱动，并拒绝 SQLite/MySQL。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 不能为空")
    url = value.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql+psycopg://")
    if not url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            f"{field_name} 仅支持 PostgreSQL（postgresql+asyncpg://），不允许 SQLite 或其他数据库"
        )
    return url


class Settings(BaseSettings):
    """后端运行配置。

    敏感项使用 SecretStr，避免 repr / 日志意外泄露；数据库 URL 仅允许 PostgreSQL。
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    app_name: str = "智能简历诊断与面试模拟平台"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    secret_key: SecretStr = SecretStr(DEFAULT_SECRET_KEY)
    access_token_expire_minutes: int = Field(default=1440, gt=0)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 数据库：应用使用 asyncpg，Alembic 迁移使用 psycopg（见 sync_database_url）
    database_url: str = "postgresql+asyncpg://resume_app:resume_app@127.0.0.1:5432/resume_platform"
    test_database_url: str = ""
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)

    # DeepSeek
    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_timeout_seconds: float = Field(default=120.0, gt=0, le=300)
    deepseek_max_retries: int = Field(default=2, ge=0, le=5)
    deepseek_max_output_tokens: int = Field(default=8192, ge=256, le=65536)

    # 文件与日志
    upload_dir: Path = BACKEND_DIR / "var" / "uploads"
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)
    log_level: str = "INFO"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> str:
        """只接受 PostgreSQL；应用统一归一为 asyncpg 驱动。

        psycopg 在 Windows 的 ProactorEventLoop 下无法异步运行，因此应用层使用
        asyncpg，Alembic 迁移则通过 sync_database_url 使用 psycopg 同步连接。
        """
        return normalize_postgres_url(value, field_name="DATABASE_URL")

    @field_validator("test_database_url", mode="before")
    @classmethod
    def normalize_test_database_url(cls, value: object) -> str:
        """测试库连接串；留空表示跳过需要数据库的测试。"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return ""
        return normalize_postgres_url(value, field_name="TEST_DATABASE_URL")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        level = value.upper()
        if level not in ALLOWED_LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL 必须是 {sorted(ALLOWED_LOG_LEVELS)} 之一")
        return level

    @model_validator(mode="after")
    def validate_production_safety(self) -> Settings:
        if self.environment == "production":
            if self.debug:
                raise ValueError("生产环境必须设置 DEBUG=false")
            secret = self.secret_key.get_secret_value()
            if secret in {"", DEFAULT_SECRET_KEY, "change-me"} or len(secret) < 32:
                raise ValueError("生产环境 SECRET_KEY 必须是至少 32 位的随机字符串")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def database_url_safe(self) -> str:
        """用于日志/健康检查的脱敏数据库标识，不含账号密码。"""
        from sqlalchemy.engine import make_url

        url = make_url(self.database_url)
        return f"{url.drivername}://{url.host or 'localhost'}:{url.port or 5432}/{url.database}"

    @property
    def sync_database_url(self) -> str:
        """Alembic 专用同步连接串（psycopg）。"""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

    @property
    def upload_path(self) -> Path:
        """上传目录；相对路径按 backend/ 解析，避免受启动目录影响。"""
        return self.upload_dir if self.upload_dir.is_absolute() else BACKEND_DIR / self.upload_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()
