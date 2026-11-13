"""注册、登录与当前用户接口。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册新用户",
)
async def register(payload: RegisterRequest, session: DbSession) -> UserResponse:
    try:
        user = await create_user(
            session,
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已注册",
        ) from None
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="登录并获取 JWT")
async def login(
    payload: LoginRequest,
    session: DbSession,
    settings: AppSettings,
) -> TokenResponse:
    try:
        user = await authenticate_user(
            session,
            email=str(payload.email),
            password=payload.password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    token, expires_in = create_access_token(user.id, settings)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse, summary="获取当前登录用户")
async def read_current_user(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
