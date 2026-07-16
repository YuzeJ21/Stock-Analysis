"""Build comparable, generated snapshots of selected-profile research state."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from src.profile_context import ProfileContext, build_profile_context


SCHEMA_VERSION = "research-change-snapshot-v1"
READINESS_FIELDS = (
    "price_ready",
    "momentum_ready",
    "market_direction_ready",
    "liquidity_ready",
    "correlation_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "earnings_ready",
    "analyst_estimates_ready",
    "portfolio_ready",
    "overall_readiness_state",
    "blocked_features",
    "excluded_features",
    "updated_at",
)
FUNDAMENTAL_FIELDS = (
    "revenue",
    "eps",
    "free_cash_flow",
    "fcf",
    "fcf_margin",
    "operating_margin",
    "profit_margin",
    "ebitda",
    "cash",
    "debt",
    "net_debt",
    "shares_outstanding",
    "market_cap",
    "enterprise_value",
    "source",
    "as_of_date",
    "updated_at",
    "sec_cik",
    "sec_form",
    "sec_filed_date",
    "sec_accession",
    "sec_entity_name",
)


@dataclass(frozen=True)
class TickerResearchState:
    ticker: str
    readiness: tuple[tuple[str, str], ...]
    fundamentals: tuple[tuple[str, str], ...]
    latest_price_date: str
    latest_filing_accession: str
    latest_filing_date: str
    nowcast_consensus_ids: tuple[str, ...]
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class ResearchChangeSnapshot:
    schema_version: str
    profile_key: str
    snapshot_identity: str
    captured_at: str
    source_as_of: str
    tickers: tuple[TickerResearchState, ...]


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return [
                {str(key): str(value or "").strip() for key, value in row.items()}
                for row in csv.DictReader(handle)
            ]
    except (OSError, UnicodeError, csv.Error):
        return []


def _ticker(value: object) -> str:
    return str(value or "").strip().upper()


def _rows_by_ticker(rows: Iterable[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        ticker = _ticker(row.get("ticker"))
        if ticker:
            result[ticker] = dict(row)
    return result


def _selected_values(row: Mapping[str, str], fields: Iterable[str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((field, str(row.get(field) or "").strip()) for field in fields if field in row))


def _latest_price_dates(rows: Iterable[Mapping[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        ticker = _ticker(row.get("ticker"))
        value = str(row.get("date") or "").strip()
        if ticker and value and value > result.get(ticker, ""):
            result[ticker] = value
    return result


def _nowcast_state(rows: Iterable[Mapping[str, str]]) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    identifiers: dict[str, set[str]] = {}
    references: dict[str, set[str]] = {}
    for row in rows:
        ticker = _ticker(row.get("ticker"))
        fiscal_period = str(row.get("fiscal_period") or "").strip()
        snapshot_at = str(row.get("snapshot_at") or "").strip()
        if not ticker or not fiscal_period or not snapshot_at:
            continue
        identifiers.setdefault(ticker, set()).add(f"{ticker}|{fiscal_period}|{snapshot_at}")
        source_ref = str(row.get("source_ref") or "").strip()
        if source_ref:
            references.setdefault(ticker, set()).add(source_ref)
    return (
        {ticker: tuple(sorted(values)) for ticker, values in identifiers.items()},
        {ticker: tuple(sorted(values)) for ticker, values in references.items()},
    )


def _fundamental_source_refs(row: Mapping[str, str]) -> tuple[str, ...]:
    refs: set[str] = set()
    source = str(row.get("source") or "").strip()
    accession = str(row.get("sec_accession") or "").strip()
    if source:
        refs.add(source)
    if accession:
        refs.add(f"sec-accession:{accession}")
    return tuple(sorted(refs))


def build_research_change_snapshot(
    project_root: Path | str = ".",
    *,
    context: ProfileContext | None = None,
    captured_at: datetime | None = None,
) -> ResearchChangeSnapshot:
    """Capture comparable state without writing or falling back across profiles."""

    selected = context or build_profile_context(project_root=project_root)
    readiness = _rows_by_ticker(_read_rows(selected.data_dir / "reports" / "ticker_readiness_report.csv"))
    fundamentals = _rows_by_ticker(_read_rows(selected.data_dir / "fundamentals.csv"))
    price_dates = _latest_price_dates(_read_rows(selected.data_dir / "prices.csv"))
    consensus_ids, consensus_refs = _nowcast_state(
        _read_rows(selected.data_dir / "earnings_nowcast" / "consensus_snapshots.csv")
    )
    tickers = sorted(set(readiness) | set(fundamentals) | set(price_dates) | set(consensus_ids))
    states: list[TickerResearchState] = []
    for ticker in tickers:
        fundamental_row = fundamentals.get(ticker, {})
        source_refs = set(_fundamental_source_refs(fundamental_row))
        source_refs.update(consensus_refs.get(ticker, ()))
        states.append(
            TickerResearchState(
                ticker=ticker,
                readiness=_selected_values(readiness.get(ticker, {}), READINESS_FIELDS),
                fundamentals=_selected_values(fundamental_row, FUNDAMENTAL_FIELDS),
                latest_price_date=price_dates.get(ticker, ""),
                latest_filing_accession=str(fundamental_row.get("sec_accession") or "").strip(),
                latest_filing_date=str(fundamental_row.get("sec_filed_date") or "").strip(),
                nowcast_consensus_ids=consensus_ids.get(ticker, ()),
                source_refs=tuple(sorted(source_refs)),
            )
        )
    captured = (captured_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    return ResearchChangeSnapshot(
        schema_version=SCHEMA_VERSION,
        profile_key=selected.profile_key,
        snapshot_identity=selected.snapshot_identity,
        captured_at=captured,
        source_as_of=selected.source_as_of,
        tickers=tuple(states),
    )


def _payload(snapshot: ResearchChangeSnapshot) -> dict[str, object]:
    return asdict(snapshot)


def write_research_change_snapshot(snapshot: ResearchChangeSnapshot, output: Path | str) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(_payload(snapshot), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def load_research_change_snapshot(path: Path | str) -> ResearchChangeSnapshot:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid research change snapshot: {exc}") from exc
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported research change snapshot schema: {payload.get('schema_version')!r}")
    try:
        states = tuple(
            TickerResearchState(
                ticker=str(row["ticker"]),
                readiness=tuple((str(key), str(value)) for key, value in row.get("readiness", [])),
                fundamentals=tuple((str(key), str(value)) for key, value in row.get("fundamentals", [])),
                latest_price_date=str(row.get("latest_price_date") or ""),
                latest_filing_accession=str(row.get("latest_filing_accession") or ""),
                latest_filing_date=str(row.get("latest_filing_date") or ""),
                nowcast_consensus_ids=tuple(str(value) for value in row.get("nowcast_consensus_ids", [])),
                source_refs=tuple(str(value) for value in row.get("source_refs", [])),
            )
            for row in payload.get("tickers", [])
        )
        return ResearchChangeSnapshot(
            schema_version=str(payload["schema_version"]),
            profile_key=str(payload["profile_key"]),
            snapshot_identity=str(payload.get("snapshot_identity") or ""),
            captured_at=str(payload["captured_at"]),
            source_as_of=str(payload.get("source_as_of") or ""),
            tickers=states,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid research change snapshot fields: {exc}") from exc
