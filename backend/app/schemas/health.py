"""健康检查与通用响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthBase(BaseModel):
    app: str
    version: str
    environment: str


class LivenessResponse(HealthBase):
    status: Literal["ok"] = "ok"
    checked_at: datetime


class HealthResponse(HealthBase):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    database_error: str | None = None
    checked_at: datetime


class MessageResponse(BaseModel):
    message: str = Field(description="面向用户的提示信息")
