"""四维诊断记录模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        Index("ix_diagnoses_user_created", "user_id", "created_at"),
        Index("ix_diagnoses_user_resume", "user_id", "resume_id", "created_at"),
        Index("ix_diagnoses_user_jd", "user_id", "jd_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    resume_version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    jd_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    jd_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(50), nullable=False)
    weights: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    format_score: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    keyword_score: Mapped[int] = mapped_column(Integer, nullable=False)
    jd_match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    format_details: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    completeness_details: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    keyword_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    jd_match_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    suggestions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
