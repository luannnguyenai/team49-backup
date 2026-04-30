from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.store import QAHistory


class AgentTutorMemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def recent_qa_for_lecture(
        self,
        lecture_id: str | None,
        context_binding_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, str]]:
        if not lecture_id and not context_binding_id:
            return []
        filters = []
        if lecture_id:
            filters.append(QAHistory.lecture_id == lecture_id)
        if context_binding_id:
            filters.append(QAHistory.context_binding_id == context_binding_id)
        result = await self.session.execute(
            select(QAHistory).where(*filters).order_by(desc(QAHistory.created_at)).limit(limit)
        )
        rows = list(result.scalars().all())
        return [
            {"question": row.question or "", "answer": row.answer or ""}
            for row in reversed(rows)
        ]
