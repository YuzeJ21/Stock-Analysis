from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.point_in_time_universe_lineage import resolve_lineage


@dataclass(frozen=True)
class Row:
    row_id: str
    parent_id: str
    scope: str
    available_at: datetime


T0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2021, 1, 1, tzinfo=timezone.utc)


def _resolve(rows, cutoff=T1):
    return resolve_lineage(
        rows,
        row_id=lambda row: row.row_id,
        parent_id=lambda row: row.parent_id,
        scope=lambda row: row.scope,
        available_at=lambda row: row.available_at,
        cutoff=cutoff,
    )


def test_selects_latest_unambiguous_leaf_available_by_cutoff():
    rows = (Row("a", "", "scope", T0), Row("b", "a", "scope", T1))

    result = _resolve(rows)

    assert result.leaves == (rows[1],)
    assert result.reason_codes == ()


def test_fork_blocks_scope_instead_of_picking_a_leaf():
    rows = (
        Row("a", "", "scope", T0),
        Row("b", "a", "scope", T1),
        Row("c", "a", "scope", T1),
    )

    result = _resolve(rows)

    assert result.leaves == ()
    assert "lineage_fork" in result.reason_codes


@pytest.mark.parametrize(
    "rows,reason",
    [
        (
            (Row("a", "", "s", T0), Row("a", "", "s", T1)),
            "lineage_duplicate_id",
        ),
        ((Row("b", "missing", "s", T1),), "lineage_missing_parent"),
        (
            (Row("a", "", "s1", T0), Row("b", "a", "s2", T1)),
            "lineage_cross_scope_parent",
        ),
        (
            (Row("a", "", "s", T0), Row("b", "", "s", T1)),
            "lineage_multiple_roots",
        ),
        (
            (Row("a", "b", "s", T0), Row("b", "a", "s", T1)),
            "lineage_cycle",
        ),
        (
            (Row("a", "", "s", T1), Row("b", "a", "s", T0)),
            "lineage_order_reversed",
        ),
    ],
)
def test_invalid_lineage_is_blocked(rows, reason):
    assert reason in _resolve(rows).reason_codes


def test_post_cutoff_revision_is_not_selected():
    rows = (Row("a", "", "scope", T0), Row("b", "a", "scope", T1))

    result = _resolve(rows, cutoff=T0)

    assert tuple(row.row_id for row in result.leaves) == ("a",)
