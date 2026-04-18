"""
routers/auth.py
---------------
Auth & user-profile routes:

    POST  /api/auth/register
    POST  /api/auth/login
    POST  /api/auth/refresh
    GET   /api/users/me
    PUT   /api/users/me/onboarding
"""

import time
import uuid
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_async_db
from src.dependencies.auth import get_current_user
from src.models.content import Module, Topic
from src.models.learning import MasteryScore
from src.middleware.rate_limit import check_rate_limit
from src.models.user import User
from src.redis_client import get_redis
from src.schemas.auth import (
    AccessToken,
    LoginRequest,
    OnboardingRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    TokenPayload,
    UserProfile,
    UserSkillOverview,
    UserSkillSnapshot,
)
from src.services.mastery_evaluator import classify_mastery
from src.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_by_id,
    register_user,
    update_onboarding,
)
from src.services.token_guard import is_payload_revoked, revoke_payload

# ---------------------------------------------------------------------------
# In-process rate limiter for login (sliding window, per IP)
# ---------------------------------------------------------------------------


class _SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter stored in memory."""

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            timestamps = [t for t in self._store[key] if t > cutoff]
            if len(timestamps) >= self._max:
                self._store[key] = timestamps
                return False
            timestamps.append(now)
            self._store[key] = timestamps
            return True


_login_limiter = _SlidingWindowRateLimiter(
    max_calls=settings.rate_limit_login_per_minute,
    window_seconds=60,
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])
users_router = APIRouter(prefix="/api/users", tags=["Users"])
_bearer = HTTPBearer(auto_error=True)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_token_pair(user: User) -> TokenPair:
    access_token, expires_in = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def _user_to_profile(user: User) -> UserProfile:
    return UserProfile.model_validate(user)


_SKILL_LABELS = [
    "Machine Learning",
    "Deep Learning",
    "Computer Vision",
    "NLP",
    "LLM",
]


def _resolve_skill_bucket(*parts: str | None) -> str | None:
    text = " ".join(part or "" for part in parts).lower()
    if any(token in text for token in ("computer vision", "3d vision", "vision and language", "vision")):
        return "Computer Vision"
    if any(token in text for token in ("natural language", "nlp", "language processing")):
        return "NLP"
    if any(token in text for token in ("llm", "language model", "prompt", "rag", "agent")):
        return "LLM"
    if "deep learning" in text:
        return "Deep Learning"
    if "machine learning" in text or " ml " in f" {text} ":
        return "Machine Learning"
    return None


async def _build_user_skill_overview(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserSkillOverview:
    result = await db.execute(
        select(MasteryScore, Topic, Module)
        .join(Topic, MasteryScore.topic_id == Topic.id)
        .join(Module, Topic.module_id == Module.id)
        .where(
            MasteryScore.user_id == user_id,
            MasteryScore.kc_id.is_(None),
        )
    )

    grouped: dict[str, list[float]] = {label: [] for label in _SKILL_LABELS}

    for mastery, topic, module in result.all():
        bucket = _resolve_skill_bucket(
            topic.name,
            topic.description,
            module.name,
            module.description,
        )
        if bucket is None:
            continue
        grouped[bucket].append(round(mastery.mastery_probability * 100, 1))

    skills = []
    for label in _SKILL_LABELS:
        if grouped[label]:
            value = round(sum(grouped[label]) / len(grouped[label]), 1)
            level = classify_mastery(value)
        else:
            value = 0.0
            level = "not_started"
        skills.append(UserSkillSnapshot(label=label, value=value, level=level))

    return UserSkillOverview(skills=skills)


async def _is_login_allowed(client_ip: str) -> bool:
    try:
        redis = get_redis()
    except RuntimeError:
        return _login_limiter.is_allowed(client_ip)

    return await check_rate_limit(
        redis,
        f"rl:login:{client_ip}",
        limit=settings.rate_limit_login_per_minute,
        window_sec=60,
    )


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


@auth_router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account and receive JWT tokens",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenPair:
    try:
        user = await register_user(db, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return _build_token_pair(user)


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@auth_router.post(
    "/login",
    response_model=TokenPair,
    summary="Authenticate with email + password and receive JWT tokens",
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
) -> TokenPair:
    # Rate limiting — key by client IP
    client_ip = request.client.host if request.client else "unknown"
    if not await _is_login_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait 60 seconds and try again.",
            headers={"Retry-After": "60"},
        )

    try:
        user = await authenticate_user(db, body.email, body.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _build_token_pair(user)


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------


@auth_router.post(
    "/refresh",
    response_model=AccessToken,
    summary="Obtain a new access token using a valid refresh token",
)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_async_db),
) -> AccessToken:
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: TokenPayload = decode_token(body.refresh_token)
    except ValueError:
        raise invalid_exc

    if await is_payload_revoked(payload):
        raise invalid_exc

    if payload.type != "refresh":
        raise invalid_exc

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        raise invalid_exc

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise invalid_exc

    access_token, expires_in = create_access_token(user.id)
    return AccessToken(access_token=access_token, expires_in=expires_in)


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


@auth_router.post(
    "/logout",
    summary="Revoke the current bearer token",
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict[str, str]:
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise invalid_exc

    await revoke_payload(payload)
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/users/me
# ---------------------------------------------------------------------------


@users_router.get(
    "/me",
    response_model=UserProfile,
    summary="Return the authenticated user's profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    return _user_to_profile(current_user)


@users_router.get(
    "/me/skills",
    response_model=UserSkillOverview,
    summary="Return the authenticated user's current AI skill overview",
)
async def get_my_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserSkillOverview:
    return await _build_user_skill_overview(db, current_user.id)


# ---------------------------------------------------------------------------
# PUT /api/users/me/onboarding
# ---------------------------------------------------------------------------


@users_router.put(
    "/me/onboarding",
    response_model=UserProfile,
    summary="Submit onboarding answers and update the user profile",
)
async def onboarding(
    body: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserProfile:
    user = await update_onboarding(db, current_user, body)
    return _user_to_profile(user)
