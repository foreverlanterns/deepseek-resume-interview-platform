"""JD 请求与响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

LIST_FIELDS = (
    "required_skills",
    "preferred_skills",
    "keywords",
    "responsibilities",
    "qualifications",
)


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in cleaned:
            cleaned.append(text[:300])
    if len(cleaned) > 50:
        raise ValueError("单个列表最多 50 项")
    return cleaned


class JobDescriptionPayload(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    raw_text: str = Field(default="", max_length=50_000)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)

    @field_validator(*LIST_FIELDS, mode="before")
    @classmethod
    def clean_lists(cls, value: object) -> list[str]:
        return _clean_list(value)

    @field_validator("company", mode="before")
    @classmethod
    def clean_company(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class JobDescriptionResponse(JobDescriptionPayload):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
