_DIFFICULTY_ORDER = {"medium": 0, "easy": 1, "hard": 2}


class CanonicalQuestionSelector:
    def __init__(self, repo):
        self.repo = repo

    async def select_for_phase(
        self,
        *,
        phase: str,
        canonical_unit_ids: list[str],
        kp_ids: list[str] | None = None,
        count: int = 5,
    ):
        candidates = await self.repo.get_items_for_phase(
            phase=phase,
            canonical_unit_ids=canonical_unit_ids,
            kp_ids=kp_ids,
            limit=max(count * 4, count),
        )
        ranked = sorted(
            candidates,
            key=lambda item: (
                _DIFFICULTY_ORDER.get(str(getattr(item, "difficulty", "medium")), 1),
                str(getattr(item, "item_id", "")),
            ),
        )
        return ranked[:count]
