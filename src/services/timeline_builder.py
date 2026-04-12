"""
services/timeline_builder.py
-----------------------------
Pure-computation module: no I/O, no DB calls.

Responsibility
--------------
Given an ordered list of (topic_id, estimated_hours) pairs and the user's
weekly capacity, produce:

1. A week assignment for each topic (greedy bin-packing).
2. A warning list if the deadline is too tight.

Algorithm
---------
Greedy first-fit:
  - Walk topics in topological order.
  - Accumulate hours into the current week.
  - When adding a topic would push the week past `available_hours_per_week`,
    start a new week — unless the topic alone exceeds capacity (it goes into
    its own week regardless).

Warning thresholds
------------------
  required_per_week > available * 1.2  → TIGHT warning
  required_per_week > available * 1.5  → VERY_TIGHT warning (both emitted)
  deadline already passed or ≤ 1 week  → DEADLINE_TOO_SOON warning

Public API
----------
build_timeline(items, available_hours_per_week, deadline) -> TimelineResult
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass
class TopicSlot:
    """Input record: one topic with its pre-determined estimated_hours."""

    topic_id: uuid.UUID
    estimated_hours: float  # 0 for 'skip' actions


@dataclass
class WeekBucket:
    """Output: topics grouped into one calendar week."""

    week: int
    topic_ids: list[uuid.UUID] = field(default_factory=list)
    total_hours: float = 0.0


@dataclass
class TimelineResult:
    """Full output of build_timeline."""

    weeks: list[WeekBucket]
    total_hours: float
    total_active_weeks: int  # weeks with at least one non-skip topic
    required_hours_per_week: float | None  # None when deadline info not supplied
    warnings: list[str]

    # Convenience: map topic_id → assigned week_number
    topic_week_map: dict[uuid.UUID, int | None] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Warning constants
# ---------------------------------------------------------------------------

_TIGHT_RATIO = 1.2  # required > available × 1.2 → TIGHT
_VERY_TIGHT_RATIO = 1.5  # required > available × 1.5 → VERY_TIGHT


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def build_timeline(
    items: list[TopicSlot],
    available_hours_per_week: float,
    deadline: date | None = None,
) -> TimelineResult:
    """
    Assign topics to calendar weeks using greedy bin-packing.

    Parameters
    ----------
    items                   : Ordered list of TopicSlots (topological order).
    available_hours_per_week: User's self-reported weekly capacity.
    deadline                : Optional target completion date.

    Returns
    -------
    TimelineResult with week assignments, total hours, and warnings.
    """
    warnings: list[str] = []
    topic_week_map: dict[uuid.UUID, int | None] = {}

    # Separate actionable items (hours > 0) from skipped ones (hours == 0)
    actionable = [s for s in items if s.estimated_hours > 0]
    skipped = [s for s in items if s.estimated_hours == 0]

    total_hours = sum(s.estimated_hours for s in actionable)

    # ── Weeks-available calculation ───────────────────────────────────────────
    weeks_available: float | None = None
    required_per_week: float | None = None

    if deadline is not None:
        today = datetime.now(UTC).date()
        days_left = (deadline - today).days
        weeks_available = max(days_left / 7, 0)

        if days_left <= 7:
            warnings.append(
                "DEADLINE_TOO_SOON: Deadline is within 1 week — "
                "không đủ thời gian để hoàn thành tất cả các topic."
            )

        if weeks_available > 0 and total_hours > 0:
            required_per_week = round(total_hours / weeks_available, 2)

            if available_hours_per_week > 0:
                ratio = required_per_week / available_hours_per_week
                if ratio > _VERY_TIGHT_RATIO:
                    warnings.append(
                        f"SCHEDULE_VERY_TIGHT: Bạn cần {required_per_week:.1f} giờ/tuần "
                        f"nhưng chỉ có {available_hours_per_week:.1f} giờ/tuần — "
                        f"cân nhắc mở rộng deadline hoặc giảm bớt module."
                    )
                elif ratio > _TIGHT_RATIO:
                    warnings.append(
                        f"SCHEDULE_TIGHT: Bạn cần {required_per_week:.1f} giờ/tuần "
                        f"(vượt {((ratio - 1) * 100):.0f}% khả năng hiện tại "
                        f"{available_hours_per_week:.1f} giờ/tuần) — lịch khá chặt."
                    )

    # ── Greedy bin-packing ────────────────────────────────────────────────────
    capacity = max(available_hours_per_week, 0.5)  # floor to avoid ZeroDivisionError
    weeks: list[WeekBucket] = []
    current_week = WeekBucket(week=1)

    for slot in actionable:
        h = slot.estimated_hours
        # If the topic alone exceeds capacity, it gets its own week
        if h > capacity and current_week.total_hours > 0:
            weeks.append(current_week)
            current_week = WeekBucket(week=len(weeks) + 1)

        # If adding this topic pushes over capacity, start a new week first
        elif current_week.total_hours + h > capacity and current_week.total_hours > 0:
            weeks.append(current_week)
            current_week = WeekBucket(week=len(weeks) + 1)

        current_week.topic_ids.append(slot.topic_id)
        current_week.total_hours = round(current_week.total_hours + h, 4)
        topic_week_map[slot.topic_id] = current_week.week

    # Flush the last (possibly partial) week
    if current_week.topic_ids:
        weeks.append(current_week)

    # Skipped topics get week_number = None
    for slot in skipped:
        topic_week_map[slot.topic_id] = None

    active_weeks = len(weeks)

    return TimelineResult(
        weeks=weeks,
        total_hours=round(total_hours, 4),
        total_active_weeks=active_weeks,
        required_hours_per_week=required_per_week,
        warnings=warnings,
        topic_week_map=topic_week_map,
    )
