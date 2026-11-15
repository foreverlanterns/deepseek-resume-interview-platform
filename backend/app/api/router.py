"""API 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    analytics,
    auth,
    diagnoses,
    health,
    interviews,
    jds,
    resume_versions,
    resumes,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
api_router.include_router(resume_versions.router)
api_router.include_router(jds.router)
api_router.include_router(diagnoses.router)
api_router.include_router(interviews.router)
api_router.include_router(analytics.router)
