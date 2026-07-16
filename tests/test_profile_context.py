import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.profile_context import build_profile_context, render_profile_context_text


READINESS_FIELDS = (
    "ticker",
    "price_ready",
    "fundamentals_ready",
    "dcf_ready",
    "peer_ready",
    "updated_at",
)


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_readiness(
    path: Path,
    *,
    ticker: str,
    price: bool = False,
    fundamentals: bool = False,
    dcf: bool = False,
    peer: bool = False,
    updated_at: str = "2026-07-15T19:30:00Z",
) -> None:
    _write_csv(
        path,
        READINESS_FIELDS,
        [
            {
                "ticker": ticker,
                "price_ready": price,
                "fundamentals_ready": fundamentals,
                "dcf_ready": dcf,
                "peer_ready": peer,
                "updated_at": updated_at,
            }
        ],
    )


def _write_feature_summary(path: Path, *, updated_at: str = "2026-07-15T19:30:00Z") -> None:
    _write_csv(path, ("feature", "ready", "updated_at"), [{"feature": "price", "ready": 1, "updated_at": updated_at}])


def _write_minimum_profile(root: Path, *, ticker: str = "NVDA") -> None:
    _write_readiness(
        root / "reports/ticker_readiness_report.csv",
        ticker=ticker,
        price=True,
        fundamentals=True,
        dcf=True,
        peer=False,
    )
    _write_feature_summary(root / "reports/feature_readiness_summary.csv")
    _write_csv(
        root / "prices.csv",
        ("ticker", "date", "close"),
        [{"ticker": ticker, "date": "2026-07-14", "close": 180.0}],
    )
    _write_csv(
        root / "fundamentals.csv",
        ("ticker", "as_of_date", "revenue"),
        [{"ticker": ticker, "as_of_date": "2026-06-30", "revenue": 1}],
    )


def _set_mtime(path: Path, timestamp: str) -> None:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    seconds = parsed.timestamp()
    os.utime(path, (seconds, seconds))


def test_profile_context_uses_only_selected_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    _write_minimum_profile(tmp_path / "data/local", ticker="LOCAL")
    _write_minimum_profile(tmp_path / "data", ticker="DEFAULT")

    context = build_profile_context(project_root=tmp_path)

    assert context.profile_key == "local"
    assert context.profile_label == "Local Research"
    assert context.data_dir == (tmp_path / "data/local").resolve()
    assert context.outputs_dir == (tmp_path / "outputs/local").resolve()
    assert context.coverage.total == 1
    assert context.coverage.price_ready == 1
    assert all("data/local" in item or item.startswith("missing:") for item in context.snapshot_inputs)


def test_missing_local_profile_does_not_fall_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    _write_minimum_profile(tmp_path / "data", ticker="DEFAULT")

    context = build_profile_context(project_root=tmp_path)

    assert context.freshness_state == "missing"
    assert context.coverage.total == 0
    assert context.source_as_of == ""
    assert context.readiness_built_at == ""


def test_context_separates_source_date_from_readiness_build_time(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    profile = tmp_path / "data/local"
    _write_minimum_profile(profile)
    _write_csv(
        profile / "peers.csv",
        ("ticker", "peer_ticker", "as_of_date"),
        [{"ticker": "NVDA", "peer_ticker": "AMD", "as_of_date": "2026-07-12"}],
    )

    context = build_profile_context(project_root=tmp_path)

    assert context.source_as_of == "2026-07-14"
    assert context.readiness_built_at == "2026-07-15T19:30:00+00:00"
    assert dict(context.lane_source_dates) == {
        "fundamentals": "2026-06-30",
        "peers": "2026-07-12",
        "prices": "2026-07-14",
    }


def test_local_snapshot_identity_is_stable_and_changes_with_selected_input(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    profile = tmp_path / "data/local"
    _write_minimum_profile(profile)

    first = build_profile_context(project_root=tmp_path).snapshot_identity
    second = build_profile_context(project_root=tmp_path).snapshot_identity
    with (profile / "prices.csv").open("a", encoding="utf-8") as handle:
        handle.write("NVDA,2026-07-15,181.0\n")
    third = build_profile_context(project_root=tmp_path).snapshot_identity

    assert first == second
    assert third != first
    assert len(first) == 64


def test_demo_snapshot_identity_uses_tracked_manifest_hashes(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "demo")
    profile = tmp_path / "data/demo"
    _write_minimum_profile(profile)
    hashes = ["a" * 64, "b" * 64]
    manifest = {
        "profile": "demo",
        "snapshot_date": "2026-06-30",
        "files": {
            "prices.csv": {"path": "data/demo/prices.csv", "sha256": hashes[0]},
            "reports/ticker_readiness_report.csv": {
                "path": "data/demo/reports/ticker_readiness_report.csv",
                "sha256": hashes[1],
            },
        },
    }
    (profile / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    expected = hashlib.sha256(json.dumps(sorted(hashes), separators=(",", ":")).encode("utf-8")).hexdigest()

    context = build_profile_context(project_root=tmp_path)

    assert context.snapshot_identity == expected
    assert context.source_as_of == "2026-06-30"


@pytest.mark.parametrize(
    ("arrange", "expected"),
    [
        ("current", "current"),
        ("stale", "stale"),
        ("missing", "missing"),
        ("mixed", "mixed"),
    ],
)
def test_profile_freshness_states(tmp_path, monkeypatch, arrange, expected):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    profile = tmp_path / "data/local"
    if arrange != "missing":
        _write_minimum_profile(profile)
        report = profile / "reports/ticker_readiness_report.csv"
        feature = profile / "reports/feature_readiness_summary.csv"
        price = profile / "prices.csv"
        fundamentals = profile / "fundamentals.csv"
        if arrange == "current":
            _set_mtime(price, "2026-07-15T18:00:00Z")
            _set_mtime(fundamentals, "2026-07-15T18:00:00Z")
            _set_mtime(report, "2026-07-15T19:30:00Z")
            _set_mtime(feature, "2026-07-15T19:30:00Z")
        elif arrange == "stale":
            _set_mtime(report, "2026-07-15T18:00:00Z")
            _set_mtime(feature, "2026-07-15T18:00:00Z")
            _set_mtime(price, "2026-07-15T19:30:00Z")
        elif arrange == "mixed":
            feature.unlink()

    context = build_profile_context(project_root=tmp_path)

    assert context.freshness_state == expected


def test_rendered_profile_context_is_compact_and_complete(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    _write_minimum_profile(tmp_path / "data/local")

    rendered = render_profile_context_text(build_profile_context(project_root=tmp_path))

    assert "Profile: Local Research" in rendered
    assert "Sources through: 2026-07-14" in rendered
    assert "Readiness built: 2026-07-15T19:30:00+00:00" in rendered
    assert "Snapshot:" in rendered
    assert "Freshness:" in rendered
    assert "Coverage: price=1/1; fundamentals=1/1; DCF=1/1; peers=0/1" in rendered


def test_source_date_after_readiness_build_date_is_stale_even_when_file_mtimes_are_current(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCK_RESEARCH_DATA_PROFILE", "local")
    profile = tmp_path / "data/local"
    _write_minimum_profile(profile)
    report = profile / "reports/ticker_readiness_report.csv"
    feature = profile / "reports/feature_readiness_summary.csv"
    _set_mtime(profile / "prices.csv", "2026-07-15T18:00:00Z")
    _set_mtime(profile / "fundamentals.csv", "2026-07-15T18:00:00Z")
    _set_mtime(report, "2026-07-15T19:30:00Z")
    _set_mtime(feature, "2026-07-15T19:30:00Z")
    _write_csv(
        profile / "fundamentals.csv",
        ("ticker", "as_of_date", "revenue"),
        [{"ticker": "NVDA", "as_of_date": "2026-07-16", "revenue": 1}],
    )
    _set_mtime(profile / "fundamentals.csv", "2026-07-15T18:00:00Z")

    context = build_profile_context(
        project_root=tmp_path,
        now=datetime(2026, 7, 16, 20, 0, tzinfo=timezone.utc),
    )

    assert context.source_as_of == "2026-07-16"
    assert context.freshness_state == "stale"
    assert "source dates are newer" in context.freshness_message.lower()
