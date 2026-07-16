import csv
from datetime import datetime, timezone
from pathlib import Path

from src.profile_context import build_profile_context
from src.research_change_snapshot import (
    build_research_change_snapshot,
    load_research_change_snapshot,
    write_research_change_snapshot,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _seed_local_profile(root: Path) -> Path:
    data_dir = root / "data" / "local"
    _write_csv(
        data_dir / "reports" / "ticker_readiness_report.csv",
        [
            {
                "ticker": "NVDA",
                "price_ready": "true",
                "momentum_ready": "true",
                "fundamentals_ready": "true",
                "dcf_ready": "true",
                "peer_ready": "false",
                "overall_readiness_state": "partial",
                "blocked_features": "peer",
                "updated_at": "2026-07-15T19:30:00Z",
            }
        ],
    )
    _write_csv(
        data_dir / "reports" / "feature_readiness_summary.csv",
        [{"feature": "price", "ready": "1", "updated_at": "2026-07-15T19:30:00Z"}],
    )
    _write_csv(
        data_dir / "fundamentals.csv",
        [
            {
                "ticker": "NVDA",
                "revenue": "215938000000",
                "eps": "4.9",
                "shares_outstanding": "24000000000",
                "source": "sec_companyfacts",
                "as_of_date": "2026-01-25",
                "sec_form": "10-K",
                "sec_filed_date": "2026-02-25",
                "sec_accession": "0001045810-26-000021",
            }
        ],
    )
    _write_csv(
        data_dir / "prices.csv",
        [
            {"date": "2026-07-14", "ticker": "NVDA", "close": "180"},
            {"date": "2026-07-15", "ticker": "NVDA", "close": "181"},
        ],
    )
    _write_csv(
        data_dir / "earnings_nowcast" / "consensus_snapshots.csv",
        [
            {
                "ticker": "NVDA",
                "fiscal_period": "FY2027-Q2",
                "snapshot_at": "2026-07-15T20:00:00Z",
                "source": "reviewed_consensus",
                "source_ref": "consensus://nvda/fy2027-q2/2026-07-15",
            }
        ],
    )
    return data_dir


def test_snapshot_contains_only_selected_profile_state(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    _seed_local_profile(tmp_path)
    _write_csv(
        tmp_path / "data" / "reports" / "ticker_readiness_report.csv",
        [{"ticker": "DEFAULT", "price_ready": "true"}],
    )

    snapshot = build_research_change_snapshot(
        project_root=tmp_path,
        captured_at=datetime(2026, 7, 15, 21, 0, tzinfo=timezone.utc),
    )

    assert snapshot.profile_key == "local"
    assert [row.ticker for row in snapshot.tickers] == ["NVDA"]
    assert snapshot.snapshot_identity == build_profile_context(project_root=tmp_path).snapshot_identity


def test_snapshot_normalizes_readiness_fundamentals_filings_and_nowcast(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    _seed_local_profile(tmp_path)

    snapshot = build_research_change_snapshot(project_root=tmp_path)
    state = snapshot.tickers[0]

    assert dict(state.readiness)["dcf_ready"] == "true"
    assert dict(state.fundamentals)["shares_outstanding"] == "24000000000"
    assert state.latest_price_date == "2026-07-15"
    assert state.latest_filing_accession == "0001045810-26-000021"
    assert state.latest_filing_date == "2026-02-25"
    assert state.nowcast_consensus_ids == ("NVDA|FY2027-Q2|2026-07-15T20:00:00Z",)
    assert "consensus://nvda/fy2027-q2/2026-07-15" in state.source_refs


def test_snapshot_write_requires_explicit_output_and_never_writes_source_data(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    data_dir = _seed_local_profile(tmp_path)
    snapshot = build_research_change_snapshot(project_root=tmp_path)
    destination = tmp_path / "outputs" / "local" / "research_changes" / "snapshot.json"

    written = write_research_change_snapshot(snapshot, destination)
    loaded = load_research_change_snapshot(destination)

    assert written == destination
    assert destination.exists()
    assert loaded == snapshot
    assert not (data_dir / "research_changes.json").exists()
