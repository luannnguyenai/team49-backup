"""
repositories/user_repo.py
-------------------------
Data access for User and auth-related profile state.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def update_hashed_password(self, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_password_changed_at(
        self,
        user: User,
        hashed_password: str,
        changed_at: datetime,
    ) -> User:
        user.hashed_password = hashed_password
        user.password_changed_at = changed_at
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
