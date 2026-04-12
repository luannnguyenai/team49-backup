"""
utils/topological_sort.py
--------------------------
Kahn's algorithm for topological ordering of topics based on
their prerequisite graph.

Public API
----------
topological_sort(topic_ids, prereq_graph) -> list[UUID]

    topic_ids   : iterable of uuid.UUID  — the full set of topics to order
    prereq_graph: dict[UUID, list[UUID]] — maps each topic_id to its direct
                  prerequisites (edges point *from* dependency *to* dependent)

Returns a list of topic UUIDs in a valid learning order — prerequisites always
appear before the topics that depend on them.

Raises
------
CycleDetectedError  — if the graph contains a cycle (should not occur in a
                      well-structured curriculum, but we guard against bad data)

Notes
-----
- Only topics present in `topic_ids` are included in the output.  A prerequisite
  that is NOT in `topic_ids` (e.g. the user already skipped it) is treated as
  already-satisfied and excluded from the ordering.
- Nodes with no prerequisites (sources) are processed in original `topic_ids`
  order to keep the output deterministic.
"""

from __future__ import annotations

import uuid
from collections import deque
from collections.abc import Iterable


class CycleDetectedError(Exception):
    """Raised when topological sort detects a cycle in the prerequisite graph."""

    def __init__(self, remaining: list[uuid.UUID]) -> None:
        ids = [str(i) for i in remaining[:5]]
        super().__init__(
            f"Cycle detected in prerequisite graph. Unresolvable nodes (first 5): {ids}"
        )
        self.remaining = remaining


def topological_sort(
    topic_ids: Iterable[uuid.UUID],
    prereq_graph: dict[uuid.UUID, list[uuid.UUID]],
) -> list[uuid.UUID]:
    """
    Return `topic_ids` in dependency order using Kahn's algorithm.

    Only inter-topic edges where *both* ends are in `topic_ids` are considered.
    Prerequisites outside the working set are treated as already satisfied.

    Parameters
    ----------
    topic_ids   : The set of topics to include in the output.
    prereq_graph: {topic_id: [prereq_topic_id, ...]}  (raw from DB JSON column)

    Returns
    -------
    list[uuid.UUID] — topologically sorted topic IDs.
    """
    working_set: set[uuid.UUID] = set(topic_ids)
    # Preserve insertion order for deterministic output
    ordered_input: list[uuid.UUID] = list(dict.fromkeys(topic_ids))

    # Build adjacency list restricted to the working set
    # edges: prereq → dependent  (prereq must come first)
    in_degree: dict[uuid.UUID, int] = {tid: 0 for tid in working_set}
    dependents: dict[uuid.UUID, list[uuid.UUID]] = {tid: [] for tid in working_set}

    for tid in working_set:
        prereqs = prereq_graph.get(tid) or []
        for prereq in prereqs:
            if prereq not in working_set:
                # Prerequisite outside our set → already satisfied, skip edge
                continue
            in_degree[tid] += 1
            dependents[prereq].append(tid)

    # Initialise queue with zero-in-degree nodes, in original order
    queue: deque[uuid.UUID] = deque(tid for tid in ordered_input if in_degree[tid] == 0)

    result: list[uuid.UUID] = []
    while queue:
        node = queue.popleft()
        result.append(node)

        # Reduce in-degree of each dependent; enqueue those that become zero
        for dep in sorted(
            dependents[node], key=lambda x: ordered_input.index(x) if x in ordered_input else 0
        ):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    if len(result) != len(working_set):
        unresolved = [tid for tid in working_set if tid not in result]
        raise CycleDetectedError(unresolved)

    return result
