"""API 路由聚合。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, health, resumes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
