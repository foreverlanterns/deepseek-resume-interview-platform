"""ORM 模型包。

新增模型后必须在此导入，Alembic autogenerate 才能发现。
"""

from __future__ import annotations

from app.models.diagnosis import Diagnosis
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.job_description import JobDescription
from app.models.resume import Resume, ResumeStatus
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
from app.models.user import User

__all__ = [
    "Diagnosis",
    "Interview",
    "InterviewQuestion",
    "JobDescription",
    "Resume",
    "ResumeStatus",
    "ResumeVersion",
    "ResumeVersionStatus",
    "User",
]
