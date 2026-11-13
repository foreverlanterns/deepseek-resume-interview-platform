"""健康检查接口：存活、整体状态、就绪探针。"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Response, status

from app.api.deps import AppSettings, DbSession
from app.schemas.health import HealthResponse, LivenessResponse
from app.services.health import ping_database

router = APIRouter(prefix="/health", tags=["health"])


def _now() -> datetime:
    return datetime.now(UTC)


@router.get("/live", response_model=LivenessResponse, summary="存活检查")
async def liveness(settings: AppSettings) -> LivenessResponse:
    return LivenessResponse(
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        checked_at=_now(),
    )


@router.get("", response_model=HealthResponse, summary="整体健康状态")
async def health(
    response: Response,
    session: DbSession,
    settings: AppSettings,
) -> HealthResponse:
    ok, error = await ping_database(session, include_detail=settings.debug)
    if not ok:
        response.status_code = status.HTTP_200_OK
    return HealthResponse(
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        status="ok" if ok else "degraded",
        database="ok" if ok else "unavailable",
        database_error=error,
        checked_at=_now(),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="就绪探针（数据库不可用时返回 503）",
)
async def readiness(
    response: Response,
    session: DbSession,
    settings: AppSettings,
) -> HealthResponse:
    ok, error = await ping_database(session, include_detail=settings.debug)
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        status="ok" if ok else "degraded",
        database="ok" if ok else "unavailable",
        database_error=error,
        checked_at=_now(),
    )
