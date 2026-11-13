"""ORM 模型包。

新增模型后必须在此导入，Alembic autogenerate 才能发现。
"""

from __future__ import annotations

from app.models.resume import Resume, ResumeStatus
from app.models.user import User

__all__ = ["Resume", "ResumeStatus", "User"]
