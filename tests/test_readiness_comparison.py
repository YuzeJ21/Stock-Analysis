import os
from pathlib import Path

import pandas as pd
import pytest

import src.readiness_comparison as comparison_module
from src.readiness_comparison import compare_readiness_snapshots, main, render_readiness_comparison
from src.readiness_engine import (
    READINESS_METHOD_VERSION,
    READINESS_SNAPSHOT_SCHEMA_VERSION,
)
from src.readiness_source_boundary import readiness_input_identity


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tree_manifest(root: Path) -> dict[str, tuple[str, bytes | None]]:
    manifest = {".": ("directory", None)}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            manifest[relative] = ("symlink", os.readlink(path).encode())
        elif path.is_dir():
            manifest[relative] = ("directory", None)
        else:
            manifest[relative] = ("file", path.read_bytes())
    return manifest


def _profile_dirs(root: Path, profile: str = "default") -> tuple[Path, Path]:
    if profile == "default":
        data_dir, output_dir = root / "data", root / "outputs"
    else:
        data_dir, output_dir = root / "data" / profile, root / "outputs" / profile
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir, output_dir


def _readiness_rows(*, aaa_state: str = "blocked", aaa_price_ready: bool = False) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "overall_readiness_state": aaa_state,
                "price_ready": aaa_price_ready,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "price fundamentals" if not aaa_price_ready else "fundamentals",
                "excluded_features": "",
                "missing_data": "price rows" if not aaa_price_ready else "revenue",
            },
            {
                "ticker": "BBB",
                "overall_readiness_state": "partial",
                "price_ready": True,
                "fundamentals_ready": False,
                "dcf_ready": False,
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "earnings_ready": False,
                "analyst_estimates_ready": False,
                "blocked_features": "fundamentals",
                "excluded_features": "",
                "missing_data": "revenue",
            },
        ]
    )


def _snapshot_frame(
    rows: pd.DataFrame,
    *,
    profile: str,
    input_identity: str,
    schema_version: str = READINESS_SNAPSHOT_SCHEMA_VERSION,
    method_version: str = READINESS_METHOD_VERSION,
) -> pd.DataFrame:
    frame = rows.copy(deep=True)
    frame["snapshot_profile"] = profile
    frame["snapshot_input_identity"] = input_identity
    frame["snapshot_captured_at"] = "2026-08-03T12:00:00+00:00"
    frame["snapshot_schema_version"] = schema_version
    frame["snapshot_method_version"] = method_version
    return frame


def _write_snapshot(
    root: Path,
    rows: pd.DataFrame,
    *,
    profile: str = "default",
    path: Path | None = None,
    input_identity: str | None = None,
) -> Path:
    data_dir, _ = _profile_dirs(root, profile)
    destination = path or data_dir / "reports" / "ticker_readiness_report.previous.csv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    identity = input_identity or readiness_input_identity(root, profile)
    _snapshot_frame(rows, profile=profile, input_identity=identity).to_csv(destination, index=False)
    return destination


def test_default_comparison_uses_selected_profile_in_memory_without_writing(tmp_path: Path, monkeypatch):
    data_dir, output_dir = _profile_dirs(tmp_path)
    before_path = _write_snapshot(tmp_path, _readiness_rows())
    contradictory = _readiness_rows(aaa_state="blocked", aaa_price_ready=False)
    contradictory["ticker"] = ["WRONG", "ALSO_WRONG"]
    contradictory.to_csv(data_dir / "reports" / "ticker_readiness_report.csv", index=False)
    current = _readiness_rows(aaa_state="partial", aaa_price_ready=True)
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_builder(*args, **kwargs):
        calls.append((args, kwargs))
        return {"ticker_readiness_report": current.copy(deep=True)}

    monkeypatch.setattr(comparison_module, "build_ticker_readiness_report", fake_builder, raising=False)
    before_manifest = _tree_manifest(tmp_path)

    comparison = compare_readiness_snapshots(tmp_path, profile="default", top_n=5)
    rendered = render_readiness_comparison(
        comparison,
        batch_id="RB-TEST",
        lane="prices",
        review_date="2026-06-12",
    )

    assert calls == [
        (
            (tmp_path.resolve(),),
            {
                "data_dir": data_dir.resolve(),
                "output_dir": output_dir.resolve(),
                "write_outputs": False,
            },
        )
    ]
    assert comparison.status == "ok"
    assert comparison.before_path == before_path
    assert comparison.after_source == "in-memory readiness profile=default"
    assert comparison.profile == "default"
    assert comparison.readiness_method_version == READINESS_METHOD_VERSION
    assert comparison.before_input_identity
    assert comparison.after_input_identity == readiness_input_identity(tmp_path, "default")
    assert comparison.before_rows == 2
    assert comparison.after_rows == 2
    assert comparison.changed_tickers == ("AAA",)
    assert "overall_readiness_state (blocked: 1->0; partial: 1->2)" in comparison.changed_readiness_counts
    assert "price_ready (not_ready: 1->0; ready: 1->2)" in comparison.changed_readiness_counts
    assert "After row set: in-memory readiness profile=default" in rendered
    assert "Read-only" in rendered
    assert "not investment advice" in rendered
    assert 'BATCH_ID="RB-TEST"' in rendered
    assert 'CHANGED_TICKERS="AAA"' in rendered
    assert "make readiness" not in rendered
    assert _tree_manifest(tmp_path) == before_manifest


def test_missing_prior_snapshot_points_only_to_same_profile_capture(tmp_path: Path, monkeypatch):
    _profile_dirs(tmp_path, "local")
    monkeypatch.setattr(
        comparison_module,
        "build_ticker_readiness_report",
        lambda *args, **kwargs: pytest.fail("current composition must not run before the prior snapshot exists"),
        raising=False,
    )

    comparison = compare_readiness_snapshots(tmp_path, profile="local")
    rendered = render_readiness_comparison(comparison)

    assert comparison.status == "missing_before"
    assert "make readiness-snapshot PROFILE=local" in rendered
    assert "make readiness " not in rendered
    assert "Changed tickers (0): none" in rendered


def test_cross_profile_prior_snapshot_is_rejected(tmp_path: Path, monkeypatch):
    _profile_dirs(tmp_path, "default")
    _profile_dirs(tmp_path, "demo")
    default_snapshot = _write_snapshot(tmp_path, _readiness_rows(), profile="default")
    monkeypatch.setattr(
        comparison_module,
        "build_ticker_readiness_report",
        lambda *args, **kwargs: pytest.fail("cross-profile metadata must fail before current composition"),
        raising=False,
    )

    comparison = compare_readiness_snapshots(
        tmp_path,
        profile="demo",
        before=default_snapshot.relative_to(tmp_path),
    )

    assert comparison.status == "invalid_before"
    assert "snapshot_profile" in comparison.blocking_message
    assert "demo" in comparison.blocking_message


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda frame: frame.drop(columns=["snapshot_profile"]), "missing metadata"),
        (
            lambda frame: frame.assign(snapshot_profile=["default", "local"]),
            "inconsistent snapshot_profile",
        ),
        (
            lambda frame: frame.assign(snapshot_schema_version="999"),
            "schema version",
        ),
        (
            lambda frame: frame.assign(snapshot_method_version="older"),
            "method version",
        ),
        (
            lambda frame: frame.assign(snapshot_input_identity=["one", "two"]),
            "inconsistent snapshot_input_identity",
        ),
    ],
)
def test_invalid_prior_snapshot_metadata_fails_closed(tmp_path: Path, monkeypatch, mutator, expected: str):
    _profile_dirs(tmp_path)
    path = _write_snapshot(tmp_path, _readiness_rows())
    frame = pd.read_csv(path, keep_default_na=False)
    mutator(frame).to_csv(path, index=False)
    monkeypatch.setattr(
        comparison_module,
        "build_ticker_readiness_report",
        lambda *args, **kwargs: pytest.fail("invalid prior metadata must fail before current composition"),
        raising=False,
    )

    comparison = compare_readiness_snapshots(tmp_path)

    assert comparison.status == "invalid_before"
    assert expected in comparison.blocking_message.lower()


def test_empty_prior_snapshot_fails_closed(tmp_path: Path, monkeypatch):
    _profile_dirs(tmp_path)
    path = _write_snapshot(tmp_path, _readiness_rows())
    pd.read_csv(path).iloc[0:0].to_csv(path, index=False)
    monkeypatch.setattr(
        comparison_module,
        "build_ticker_readiness_report",
        lambda *args, **kwargs: pytest.fail("empty prior snapshot must fail before current composition"),
        raising=False,
    )

    comparison = compare_readiness_snapshots(tmp_path)

    assert comparison.status == "invalid_before"
    assert "empty" in comparison.blocking_message.lower()


def test_current_composition_failure_blocks_without_tracked_report_fallback(tmp_path: Path, monkeypatch):
    data_dir, _ = _profile_dirs(tmp_path)
    _write_snapshot(tmp_path, _readiness_rows())
    _write(data_dir / "reports" / "ticker_readiness_report.csv", "ticker,overall_readiness_state\nFALLBACK,ready\n")
    monkeypatch.setattr(
        comparison_module,
        "build_ticker_readiness_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("composition unavailable")),
        raising=False,
    )

    comparison = compare_readiness_snapshots(tmp_path)

    assert comparison.status == "current_composition_blocked"
    assert "composition unavailable" in comparison.blocking_message
    assert comparison.after_rows == 0
    assert "FALLBACK" not in comparison.changed_tickers


def test_explicit_before_and_after_fixtures_require_matching_snapshot_contract(tmp_path: Path):
    _profile_dirs(tmp_path)
    before = _write_snapshot(tmp_path, _readiness_rows(), path=tmp_path / "fixtures" / "before.csv")
    after_identity = "after-input-identity"
    after = tmp_path / "fixtures" / "after.csv"
    _snapshot_frame(
        _readiness_rows(aaa_state="partial", aaa_price_ready=True),
        profile="default",
        input_identity=after_identity,
    ).to_csv(after, index=False)

    comparison = compare_readiness_snapshots(
        tmp_path,
        before=before.relative_to(tmp_path),
        after=after.relative_to(tmp_path),
        profile="default",
    )

    assert comparison.status == "ok"
    assert comparison.after_source == str(after)
    assert comparison.after_input_identity == after_identity
    assert comparison.changed_tickers == ("AAA",)


def test_main_returns_nonzero_for_comparison_blocker(tmp_path: Path, capsys):
    _profile_dirs(tmp_path)

    exit_code = main(["--root", str(tmp_path), "--profile", "default"])

    assert exit_code == 2
    assert "make readiness-snapshot PROFILE=default" in capsys.readouterr().out


@pytest.mark.parametrize("unsafe_kind", ["reports_symlink", "snapshot_symlink", "reports_file"])
def test_default_prior_snapshot_read_rejects_unsafe_physical_paths(
    tmp_path: Path,
    monkeypatch,
    unsafe_kind: str,
):
    data_dir, _ = _profile_dirs(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    external_snapshot = external / "ticker_readiness_report.previous.csv"
    _snapshot_frame(
        _readiness_rows(),
        profile="default",
        input_identity=readiness_input_identity(tmp_path, "default"),
    ).to_csv(external_snapshot, index=False)
    reports = data_dir / "reports"
    if unsafe_kind == "reports_symlink":
        reports.symlink_to(external, target_is_directory=True)
    elif unsafe_kind == "snapshot_symlink":
        reports.mkdir()
        (reports / "ticker_readiness_report.previous.csv").symlink_to(external_snapshot)
    else:
        reports.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(
        comparison_module,
        "build_ticker_readiness_report",
        lambda *args, **kwargs: pytest.fail("unsafe prior paths must fail before current composition"),
        raising=False,
    )

    comparison = compare_readiness_snapshots(tmp_path, profile="default")

    assert comparison.status == "invalid_before"
    assert any(term in comparison.blocking_message.lower() for term in ("symbolic link", "regular file", "directory"))


def test_invalid_utf8_and_malformed_csv_fail_closed_for_before_and_after(tmp_path: Path):
    data_dir, _ = _profile_dirs(tmp_path)
    before = data_dir / "reports" / "ticker_readiness_report.previous.csv"
    before.parent.mkdir()
    before.write_bytes(b"ticker,snapshot_profile\nAAA,\xff\n")

    invalid_before = compare_readiness_snapshots(tmp_path)

    assert invalid_before.status == "invalid_before"
    assert "utf-8" in invalid_before.blocking_message.lower()

    _write_snapshot(tmp_path, _readiness_rows())
    malformed_after = tmp_path / "fixtures" / "after.csv"
    malformed_after.parent.mkdir()
    malformed_after.write_text('ticker,snapshot_profile\n"unterminated', encoding="utf-8")

    invalid_after = compare_readiness_snapshots(tmp_path, after=malformed_after)

    assert invalid_after.status == "invalid_after"
    assert "csv" in invalid_after.blocking_message.lower()


def test_default_prior_snapshot_open_race_fails_closed(tmp_path: Path, monkeypatch):
    _profile_dirs(tmp_path)
    before = _write_snapshot(tmp_path, _readiness_rows())
    real_open = comparison_module.os.open

    def racing_open(path, flags):
        if Path(path) == before:
            raise OSError("replaced during open")
        return real_open(path, flags)

    monkeypatch.setattr(comparison_module.os, "open", racing_open)

    comparison = compare_readiness_snapshots(tmp_path)

    assert comparison.status == "invalid_before"
    assert "changed before it could be read safely" in comparison.blocking_message.lower()


def test_main_returns_two_for_invalid_utf8_snapshot(tmp_path: Path, capsys):
    data_dir, _ = _profile_dirs(tmp_path)
    snapshot = data_dir / "reports" / "ticker_readiness_report.previous.csv"
    snapshot.parent.mkdir()
    snapshot.write_bytes(b"ticker,snapshot_profile\nAAA,\xff\n")

    exit_code = main(["--root", str(tmp_path), "--profile", "default"])

    assert exit_code == 2
    assert "invalid_before" in capsys.readouterr().out
