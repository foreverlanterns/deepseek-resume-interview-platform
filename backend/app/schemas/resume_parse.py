"""简历结构化数据模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            cleaned.append(text[:2000])
    return cleaned


class ParsedModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    @field_validator(
        "details", "highlights", "tech_stack", "items", mode="before", check_fields=False
    )
    @classmethod
    def clean_string_lists(cls, value: object) -> list[str]:
        return _clean_string_list(value)

    @field_validator("source_text", mode="before", check_fields=False)
    @classmethod
    def clean_source_text(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text[:2000] or None


class BasicInfo(ParsedModel):
    name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=200)
    headline: str | None = Field(default=None, max_length=300)
    source_text: str | None = None


class EducationItem(ParsedModel):
    school: str = Field(min_length=1, max_length=200)
    degree: str | None = Field(default=None, max_length=100)
    major: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=50)
    end_date: str | None = Field(default=None, max_length=50)
    details: list[str] = Field(default_factory=list)
    source_text: str | None = None


class WorkItem(ParsedModel):
    company: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=50)
    end_date: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=200)
    highlights: list[str] = Field(default_factory=list)
    source_text: str | None = None


class ProjectItem(ParsedModel):
    name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=50)
    end_date: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)
    highlights: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    source_text: str | None = None


class SkillGroup(ParsedModel):
    category: str = Field(min_length=1, max_length=100)
    items: list[str] = Field(default_factory=list)
    source_text: str | None = None


class CertificateItem(ParsedModel):
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    date: str | None = Field(default=None, max_length=50)
    source_text: str | None = None


class AwardItem(ParsedModel):
    name: str = Field(min_length=1, max_length=200)
    date: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    source_text: str | None = None


class LanguageItem(ParsedModel):
    name: str = Field(min_length=1, max_length=100)
    level: str | None = Field(default=None, max_length=100)


class ParsedResume(ParsedModel):
    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    summary: str | None = Field(default=None, max_length=3000)
    education: list[EducationItem] = Field(default_factory=list)
    work_experience: list[WorkItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    skills: list[SkillGroup] = Field(default_factory=list)
    certificates: list[CertificateItem] = Field(default_factory=list)
    awards: list[AwardItem] = Field(default_factory=list)
    languages: list[LanguageItem] = Field(default_factory=list)
