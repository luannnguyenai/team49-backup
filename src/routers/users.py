from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from src.routers.auth import get_db, User, decode_token

router = APIRouter(prefix="/api/users", tags=["users"])
bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_token(credentials.credentials, "access")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_onboarded: bool
    available_hours_per_week: Optional[float] = None

    class Config:
        from_attributes = True


class OnboardingRequest(BaseModel):
    available_hours_per_week: Optional[float] = None
    target_deadline: Optional[str] = None
    preferred_method: Optional[str] = None


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_onboarded=current_user.is_onboarded,
        available_hours_per_week=current_user.available_hours_per_week,
    )


@router.put("/me/onboarding", response_model=UserResponse)
def update_onboarding(
    req: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.available_hours_per_week is not None:
        current_user.available_hours_per_week = req.available_hours_per_week
    current_user.is_onboarded = True
    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_onboarded=current_user.is_onboarded,
        available_hours_per_week=current_user.available_hours_per_week,
    )
