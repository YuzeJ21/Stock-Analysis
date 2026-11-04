"""Verified, read-only counts from one saved ticker-readiness report."""

from __future__ import annotations

import csv
from pathlib import Path


READINESS_FIELDS = (
    "price_ready",
    "momentum_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
)
TRUE_VALUES = frozenset({"true", "1", "yes", "y", "ready"})
FALSE_VALUES = frozenset({"false", "0", "no", "n", "not_ready"})


def parse_readiness_flag(value: object) -> bool | None:
    normalized = str(value if value is not None else "").strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def inspect_saved_readiness(path: Path, allowed: set[str] | None = None) -> dict[str, object]:
    unavailable: dict[str, object] = {
        "status": "unavailable", "total": None,
        **{field: None for field in READINESS_FIELDS},
    }
    if not path.is_file():
        return unavailable
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "ticker" not in reader.fieldnames:
                return unavailable
            rows = []
            for row in reader:
                if None in row:
                    return unavailable
                ticker = str(row.get("ticker") or "").strip().upper()
                if ticker and (allowed is None or ticker in allowed):
                    rows.append(row)
    except (OSError, UnicodeError, csv.Error):
        return unavailable
    if not rows:
        return unavailable
    counts: dict[str, int | None] = {}
    for field in READINESS_FIELDS:
        if field not in reader.fieldnames:
            counts[field] = None
            continue
        values = [parse_readiness_flag(row.get(field)) for row in rows]
        counts[field] = sum(value is True for value in values) if all(value is not None for value in values) else None
    return {"status": "available", "total": len(rows), **counts}


def coverage_fraction(population: dict[str, object], field: str) -> str:
    if population.get("status") != "available":
        return "unavailable"
    total = population.get("total")
    value = population.get(field)
    if not isinstance(total, int) or total <= 0 or not isinstance(value, int) or value < 0 or value > total:
        return "unavailable"
    return f"{value}/{total}"
