from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Generic, Iterable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class LineageResult(Generic[T]):
    leaves: tuple[T, ...]
    excluded: tuple[T, ...]
    reason_codes: tuple[str, ...]


def resolve_lineage(
    records: Iterable[T],
    *,
    row_id: Callable[[T], str],
    parent_id: Callable[[T], str],
    scope: Callable[[T], str],
    available_at: Callable[[T], datetime],
    cutoff: datetime,
) -> LineageResult[T]:
    eligible = tuple(record for record in records if available_at(record) <= cutoff)
    ids = [row_id(record) for record in eligible]
    reasons: set[str] = set()
    if len(ids) != len(set(ids)):
        reasons.add("lineage_duplicate_id")

    by_id = {row_id(record): record for record in eligible}
    children: dict[str, list[T]] = {}
    roots: dict[str, list[T]] = {}
    for record in eligible:
        parent = parent_id(record)
        record_scope = scope(record)
        if not parent:
            roots.setdefault(record_scope, []).append(record)
            continue
        prior = by_id.get(parent)
        if prior is None:
            reasons.add("lineage_missing_parent")
            continue
        if scope(prior) != record_scope:
            reasons.add("lineage_cross_scope_parent")
        if available_at(record) <= available_at(prior):
            reasons.add("lineage_order_reversed")
        children.setdefault(parent, []).append(record)

    if any(len(value) > 1 for value in roots.values()):
        reasons.add("lineage_multiple_roots")
    if any(len(value) > 1 for value in children.values()):
        reasons.add("lineage_fork")

    for start in eligible:
        seen: set[str] = set()
        current = start
        while parent_id(current):
            current_id = row_id(current)
            if current_id in seen:
                reasons.add("lineage_cycle")
                break
            seen.add(current_id)
            parent = by_id.get(parent_id(current))
            if parent is None:
                break
            current = parent

    if reasons:
        return LineageResult((), eligible, tuple(sorted(reasons)))

    leaves = tuple(record for record in eligible if row_id(record) not in children)
    return LineageResult(
        leaves,
        tuple(record for record in eligible if record not in leaves),
        (),
    )
