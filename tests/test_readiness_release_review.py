from __future__ import annotations

import csv
import json
import shlex
import subprocess
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import pytest

from src import readiness_release_review as release
from src.commercial_source_rights import SourceRights


EXPECTED_CANDIDATE_PATHS = (
    "data/analyst_estimates_readiness.csv",
    "data/dcf_readiness.csv",
    "data/earnings_readiness.csv",
    "data/price_coverage_report.csv",
    "data/reports/analyst_estimates_readiness_report.csv",
    "data/reports/data_source_status.csv",
    "data/reports/dcf_readiness_report.csv",
    "data/reports/earnings_readiness_report.csv",
    "data/reports/feature_readiness_summary.csv",
    "data/reports/fundamentals_coverage_report.csv",
    "data/reports/peer_readiness_report.csv",
    "data/reports/peer_unlock_worklist.csv",
    "data/reports/price_coverage_report.csv",
    "data/reports/ticker_readiness_report.csv",
    "data/reports/universe_coverage_report.csv",
    "data/universe_master.csv",
    "outputs/feature_readiness_summary.csv",
    "outputs/peer_unlock_worklist.csv",
)


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _write(root: Path, relative: str, payload: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _release_repo(
    tmp_path: Path,
    *,
    head_ticker_readiness: dict[str, object] | None = None,
    working_ticker_readiness: dict[str, object] | None = None,
) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "tests@example.com")
    _run_git(root, "config", "user.name", "Release Tests")
    for relative in EXPECTED_CANDIDATE_PATHS:
        _write(root, relative, "ticker,status\nAAA,head\n")
    for relative in release.READINESS_SOURCE_PATHS:
        _write(root, relative, "ticker,value\nAAA,1\n")
    _write(root, release.RIGHTS_REGISTRY_PATH, "sources: []\n")
    for relative in release.PROOF_LEDGER_PATHS:
        _write(root, relative, "id,status\nproof-1,reviewed\n")
    _fundamentals().to_csv(root / "data/fundamentals.csv", index=False)
    if head_ticker_readiness is not None:
        pd.DataFrame([head_ticker_readiness]).to_csv(
            root / "data/reports/ticker_readiness_report.csv",
            index=False,
        )
    _run_git(root, "add", "--", ".")
    _run_git(root, "commit", "-qm", "seed release fixture")
    for relative in EXPECTED_CANDIDATE_PATHS:
        _write(root, relative, "ticker,status\nAAA,working\n")
    if working_ticker_readiness is not None:
        pd.DataFrame([working_ticker_readiness]).to_csv(
            root / "data/reports/ticker_readiness_report.csv",
            index=False,
        )
    return root


def _build_review(root: Path, **kwargs: object):
    proposed = pd.read_csv(root / "data/reports/ticker_readiness_report.csv")
    return release.build_release_review(
        root,
        proposed_readiness=proposed,
        rights_registry=_rights_registry(),
        **kwargs,
    )


def _record_review(root: Path, receipt: str, **overrides: object):
    proposed = pd.read_csv(root / "data/reports/ticker_readiness_report.csv")
    values: dict[str, object] = {
        "preview_receipt": receipt,
        "reviewer": "Y. Jian",
        "review_date": "2026-08-09",
        "technical_decision": "approved",
        "distribution_decision": "external_review_required",
        "confirm_reviewed": True,
        "proposed_readiness": proposed,
        "rights_registry": _rights_registry(),
    }
    values.update(overrides)
    return release.record_review(root, **values)


def test_candidate_manifest_is_exact_ordered_and_digest_is_deterministic(tmp_path: Path):
    root = _release_repo(tmp_path)

    first = _build_review(root, top_n=1)
    second = _build_review(root, top_n=50)

    assert tuple(item.path for item in first.candidate_paths) == EXPECTED_CANDIDATE_PATHS
    assert first.candidate_manifest_digest == second.candidate_manifest_digest
    assert first.preview_receipt == second.preview_receipt
    assert len(first.preview_receipt) == 64


def test_review_rejects_unexpected_modified_and_staged_paths(tmp_path: Path):
    root = _release_repo(tmp_path)
    _write(root, "data/reports/unexpected.csv", "value\n1\n")
    _run_git(root, "add", "--", "data/reports/unexpected.csv")

    packet = _build_review(root)

    assert "unexpected_changed_path:data/reports/unexpected.csv" in packet.blockers
    assert "staged_path:data/reports/unexpected.csv" in packet.blockers
    assert packet.axis("staging_hygiene_review").status == "blocked"


def test_review_rejects_a_staged_candidate_without_changing_its_digest(tmp_path: Path):
    root = _release_repo(tmp_path)
    path = EXPECTED_CANDIDATE_PATHS[0]
    before = _build_review(root).candidate_paths[0].working_sha256
    _run_git(root, "add", "--", path)

    packet = _build_review(root)

    assert f"staged_path:{path}" in packet.blockers
    assert packet.candidate_paths[0].working_sha256 == before


def test_canonical_receipt_is_key_order_independent_and_value_sensitive():
    first = release.canonical_receipt({"b": [2, 3], "a": {"x": True}})
    reordered = release.canonical_receipt({"a": {"x": True}, "b": [2, 3]})
    changed = release.canonical_receipt({"a": {"x": False}, "b": [2, 3]})

    assert first == reordered
    assert changed != first


def test_review_rejects_candidate_symlink(tmp_path: Path):
    root = _release_repo(tmp_path)
    relative = EXPECTED_CANDIDATE_PATHS[0]
    target = root / "target.csv"
    target.write_text("ticker,status\nAAA,working\n", encoding="utf-8")
    (root / relative).unlink()
    (root / relative).symlink_to(target)

    with pytest.raises(release.ReleaseReviewError, match=f"symlink_rejected:{relative}"):
        _build_review(root)


def test_review_rejects_oversized_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _release_repo(tmp_path)
    relative = EXPECTED_CANDIDATE_PATHS[0]
    monkeypatch.setattr(release, "MAX_EVIDENCE_FILE_BYTES", 64)
    _write(root, relative, "ticker,status\nAAA," + ("x" * 80) + "\n")

    with pytest.raises(release.ReleaseReviewError, match=f"file_too_large:{relative}"):
        _build_review(root)


def test_review_rejects_candidate_over_row_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = _release_repo(tmp_path)
    relative = EXPECTED_CANDIDATE_PATHS[0]
    monkeypatch.setattr(release, "MAX_EVIDENCE_CSV_ROWS", 2)
    _write(root, relative, "ticker,status\nAAA,one\nBBB,two\nCCC,three\n")

    with pytest.raises(release.ReleaseReviewError, match=f"csv_row_limit_exceeded:{relative}"):
        _build_review(root)


def test_review_rejects_duplicate_columns_and_duplicate_tickers(tmp_path: Path):
    duplicate_columns = _release_repo(tmp_path / "columns")
    relative = EXPECTED_CANDIDATE_PATHS[0]
    _write(duplicate_columns, relative, "ticker,ticker\nAAA,AAA\n")

    with pytest.raises(release.ReleaseReviewError, match=f"duplicate_csv_column:{relative}:ticker"):
        _build_review(duplicate_columns)

    duplicate_tickers = _release_repo(tmp_path / "tickers")
    _write(duplicate_tickers, relative, "ticker,status\nAAA,one\nAAA,two\n")

    with pytest.raises(release.ReleaseReviewError, match=f"duplicate_ticker:{relative}:AAA"):
        _build_review(duplicate_tickers)


def _readiness_row(ticker: str, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "ticker": ticker,
        "overall_readiness_state": "blocked",
        "price_ready": False,
        "momentum_ready": False,
        "fundamentals_ready": False,
        "dcf_ready": False,
        "peer_ready": False,
        "earnings_ready": False,
        "analyst_estimates_ready": False,
        "ready_features": "",
        "partial_features": "",
        "blocked_features": "fundamentals, dcf",
        "excluded_features": "",
    }
    row.update(overrides)
    return row


def _rights_registry() -> dict[str, SourceRights]:
    common = {
        "permitted_use": "source_backed_facts",
        "redistribution": "derived_data_only",
        "storage_limits": "reviewed local facts",
        "attribution": "required",
        "rate_limits": "provider terms",
        "authentication": "provider specific",
        "expected_freshness": "source driven",
        "fallback_priority": 1,
    }
    return {
        "sec_companyfacts": SourceRights(
            source_id="sec_companyfacts",
            display_name="SEC Companyfacts",
            commercial_use="approved",
            supported_fields=("revenue", "free_cash_flow", "fcf_margin", "shares_outstanding"),
            **common,
        ),
        "approved_prices": SourceRights(
            source_id="approved_prices",
            display_name="Approved prices",
            commercial_use="approved",
            supported_fields=("prices",),
            **common,
        ),
        "yfinance": SourceRights(
            source_id="yfinance",
            display_name="yfinance",
            commercial_use="unverified",
            supported_fields=("prices",),
            **common,
        ),
    }


def _fundamentals(source: str = "sec_companyfacts") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": source,
                "as_of_date": "2025-12-31",
                "source_ref": "filing-1",
                "revenue": 100,
                "free_cash_flow": 10,
                "fcf_margin": 0.1,
                "shares_outstanding": 5,
            }
        ]
    )


def test_three_way_review_uses_head_working_and_proposed_as_distinct_frames():
    head = pd.DataFrame([_readiness_row("AAA")])
    working = pd.DataFrame(
        [_readiness_row("AAA", fundamentals_ready=True, ready_features="fundamentals", blocked_features="dcf")]
    )

    review = release.review_release_axes(
        head,
        working,
        working.copy(),
        _fundamentals(),
        pd.DataFrame(),
        rights_registry=_rights_registry(),
        before_snapshot_identity="sha256:before",
        after_snapshot_identity="sha256:after",
    )

    assert review.head_to_working.changed_ticker_count == 1
    assert review.working_to_proposed.changed_ticker_count == 0
    assert review.axis("technical_transition_review").status == "passed"
    assert review.axis("provenance_review").status == "passed"
    assert review.axis("commercial_rights_review").status == "passed"
    assert review.axis("registered_field_scope_review").status == "passed"


def test_composite_source_and_registered_scope_fail_as_independent_axes():
    head = pd.DataFrame([_readiness_row("AAA")])
    working = pd.DataFrame([_readiness_row("AAA", fundamentals_ready=True)])

    review = release.review_release_axes(
        head,
        working,
        working.copy(),
        _fundamentals("sec_companyfacts + yfinance"),
        pd.DataFrame(),
        rights_registry=_rights_registry(),
        before_snapshot_identity="sha256:before",
        after_snapshot_identity="sha256:after",
    )

    assert review.axis("provenance_review").status == "passed"
    assert review.axis("commercial_rights_review").status == "blocked"
    assert review.axis("registered_field_scope_review").status == "blocked"
    assert "commercial_rights:unknown_source:AAA" in review.blockers
    assert "registered_field_scope_incomplete:AAA" in review.blockers


def test_dcf_price_lineage_stays_independent_from_fundamentals_evidence():
    head = pd.DataFrame([_readiness_row("AAA")])
    working = pd.DataFrame([_readiness_row("AAA", fundamentals_ready=True, dcf_ready=True)])
    prices = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "date": "2026-08-08",
                "close": 20,
                "source": "yfinance",
                "source_ref": "quote-1",
                "retrieved_at": "2026-08-08T21:00:00Z",
            }
        ]
    )

    review = release.review_release_axes(
        head,
        working,
        working.copy(),
        _fundamentals(),
        prices,
        rights_registry=_rights_registry(),
        review_cutoff="2026-08-09T00:00:00Z",
        before_snapshot_identity="sha256:before",
        after_snapshot_identity="sha256:after",
    )

    assert review.axis("provenance_review").status == "passed"
    assert review.axis("price_lineage_review").status == "blocked"
    assert "price_lineage_review_required" in review.blockers


def test_historical_binding_requires_exact_lane_source_input_cutoff_and_snapshots():
    transition = release.TransitionEvidence(
        ticker="AAA",
        fields=("fundamentals_ready",),
        source_id="sec_companyfacts",
        source_reference="filing-1",
        as_of_date="2025-12-31",
        changed_input_identity="sha256:input",
        review_cutoff="2026-08-09",
        before_snapshot_identity="sha256:before",
        after_snapshot_identity="sha256:after",
    )
    exact = {
        "lane": "fundamentals",
        "tickers": "AAA",
        "source_id": "sec_companyfacts",
        "changed_input_identity": "sha256:input",
        "review_cutoff": "2026-08-09",
        "pre_run_readiness_snapshot": "sha256:before",
        "post_run_readiness_snapshot": "sha256:after",
    }
    ticker_only = {**exact, "post_run_readiness_snapshot": "sha256:different"}

    assert release.review_historical_binding((transition,), (exact,), ()).status == "passed"
    blocked = release.review_historical_binding((transition,), (ticker_only,), ())
    assert blocked.status == "blocked"
    assert blocked.blockers == ("historical_proof_binding_missing:AAA",)


def test_mirror_review_reports_the_exact_broken_pair():
    payloads = {relative: b"same\n" for relative in EXPECTED_CANDIDATE_PATHS}
    payloads["outputs/feature_readiness_summary.csv"] = b"different\n"

    axis = release.review_candidate_mirrors(payloads)

    assert axis.status == "blocked"
    assert axis.blockers == ("mirror_mismatch:feature_readiness_summary",)


def test_build_release_review_binds_three_way_axes_and_transitions(tmp_path: Path):
    head = _readiness_row("AAA")
    working = _readiness_row(
        "AAA",
        fundamentals_ready=True,
        ready_features="fundamentals",
        blocked_features="dcf",
    )
    root = _release_repo(
        tmp_path,
        head_ticker_readiness=head,
        working_ticker_readiness=working,
    )

    packet = _build_review(root, top_n=1)

    assert packet.head_to_working.changed_ticker_count == 1
    assert packet.working_to_proposed.changed_ticker_count == 0
    assert packet.transitions[0].ticker == "AAA"
    assert tuple(axis.name for axis in packet.axes) == release.AXIS_NAMES
    assert packet.axis("technical_transition_review").status == "passed"
    assert packet.axis("candidate_integrity").status == "passed"


def test_record_requires_exact_receipt_and_appends_one_immutable_row(tmp_path: Path):
    root = _release_repo(tmp_path)
    packet = _build_review(root)

    record = _record_review(root, packet.preview_receipt)

    rows = release.load_review_records(root / release.REVIEW_RECORD_PATH)
    assert rows == (record,)
    assert record.record_id == f"RRR-20260809-{packet.preview_receipt[:12]}"
    assert record.preview_receipt == packet.preview_receipt
    assert record.distribution_decision == "external_review_required"
    assert record.research_only_boundary == "research_only_no_investment_or_execution_action"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("reviewer", "<reviewer>", "invalid_reviewer"),
        ("reviewer", "name\nsecond", "invalid_reviewer"),
        ("review_date", "08/09/2026", "invalid_review_date"),
        ("technical_decision", "maybe", "invalid_technical_decision"),
        ("distribution_decision", "assumed", "invalid_distribution_decision"),
        ("confirm_reviewed", False, "confirm_reviewed_required"),
    ],
)
def test_record_validation_failure_writes_nothing(
    tmp_path: Path,
    field: str,
    value: object,
    error: str,
):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt

    with pytest.raises(release.ReleaseReviewError, match=error):
        _record_review(root, receipt, **{field: value})

    assert not (root / release.REVIEW_RECORD_PATH).exists()


def test_record_revalidates_inside_lock_and_refuses_stale_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt
    original_lock = release.ledger_write_lock

    @contextmanager
    def mutate_after_lock(path: Path):
        with original_lock(path) as locked:
            _write(root, EXPECTED_CANDIDATE_PATHS[0], "ticker,status\nAAA,changed-after-preview\n")
            yield locked

    monkeypatch.setattr(release, "ledger_write_lock", mutate_after_lock)

    with pytest.raises(release.ReleaseReviewError, match="preview_receipt_mismatch"):
        _record_review(root, receipt)

    assert not (root / release.REVIEW_RECORD_PATH).exists()


def test_record_rejects_duplicate_receipt_without_appending(tmp_path: Path):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt
    first = _record_review(root, receipt)
    before = (root / release.REVIEW_RECORD_PATH).read_bytes()

    with pytest.raises(release.ReleaseReviewError, match="duplicate_preview_receipt"):
        _record_review(root, receipt, reviewer="Second Reviewer")

    assert (root / release.REVIEW_RECORD_PATH).read_bytes() == before
    assert release.load_review_records(root / release.REVIEW_RECORD_PATH) == (first,)


def test_record_replace_failure_preserves_the_prior_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt
    destination = root / release.REVIEW_RECORD_PATH

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("replace unavailable")

    monkeypatch.setattr(release.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace unavailable"):
        _record_review(root, receipt)

    assert not destination.exists()


def test_load_review_records_rejects_duplicate_record_id_and_receipt(tmp_path: Path):
    path = tmp_path / "reviews.csv"
    row = {column: "value" for column in release.REVIEW_RECORD_COLUMNS}
    row.update(
        {
            "record_id": "RRR-20260809-aaaaaaaaaaaa",
            "preview_receipt": "a" * 64,
            "review_date": "2026-08-09",
            "technical_decision": "approved",
            "distribution_decision": "approved",
        }
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=release.REVIEW_RECORD_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
        writer.writerow(row)

    with pytest.raises(release.ReleaseReviewError, match="duplicate_record_id"):
        release.load_review_records(path)


def test_post_write_reload_error_reports_uncertain_outcome_by_record_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt
    original_load = release.load_review_records
    calls = 0

    def fail_post_write_reload(path: Path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise release.ReleaseReviewError("simulated_reload_failure")
        return original_load(path)

    monkeypatch.setattr(release, "load_review_records", fail_post_write_reload)

    with pytest.raises(
        release.ReleaseReviewError,
        match=f"record_write_outcome_uncertain:RRR-20260809-{receipt[:12]}:reload_by_record_id",
    ):
        _record_review(root, receipt)

    assert original_load(root / release.REVIEW_RECORD_PATH)[0].preview_receipt == receipt


def test_record_appends_a_new_receipt_without_rewriting_the_prior_row(tmp_path: Path):
    root = _release_repo(tmp_path)
    first_packet = _build_review(root)
    first = _record_review(root, first_packet.preview_receipt)
    _write(root, "data/fundamentals.csv", "ticker,source\nAAA,changed_source\n")
    proposed = pd.read_csv(root / "data/reports/ticker_readiness_report.csv")
    second_packet = release.build_release_review(
        root,
        allow_record_path_change=True,
        proposed_readiness=proposed,
        rights_registry=_rights_registry(),
    )

    second = _record_review(root, second_packet.preview_receipt, review_date="2026-08-10")

    assert release.load_review_records(root / release.REVIEW_RECORD_PATH) == (first, second)


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def _evaluate_guard(root: Path, record_id: str):
    proposed = pd.read_csv(root / "data/reports/ticker_readiness_report.csv")
    return release.evaluate_guard(
        root,
        record_id=record_id,
        proposed_readiness=proposed,
        rights_registry=_rights_registry(),
    )


def test_guard_refuses_external_review_required_and_is_write_free(tmp_path: Path):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt
    record = _record_review(root, receipt, distribution_decision="external_review_required")
    before = _tree_snapshot(root)

    result = _evaluate_guard(root, record.record_id)

    assert result.status == "blocked"
    assert result.blockers == ("distribution_decision_not_approved",)
    assert _tree_snapshot(root) == before


def test_guard_passes_only_exact_approved_record_and_prints_named_paths(tmp_path: Path):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt
    record = _record_review(root, receipt, distribution_decision="approved")

    result = _evaluate_guard(root, record.record_id)
    rendered = release.render_guard(result)

    assert result.status == "passed"
    assert result.stage_paths == (release.REVIEW_RECORD_PATH, *EXPECTED_CANDIDATE_PATHS)
    assert rendered.endswith(
        "git add -- " + " ".join(shlex.quote(path) for path in result.stage_paths)
    )
    assert "git add -A" not in rendered
    assert _run_git(root, "diff", "--cached", "--name-only").stdout == ""


def test_guard_reports_exact_stale_dependency_without_writing(tmp_path: Path):
    root = _release_repo(tmp_path)
    receipt = _build_review(root).preview_receipt
    record = _record_review(root, receipt, distribution_decision="approved")
    _write(root, "data/prices.csv", "ticker,date,close\nAAA,2026-08-09,22\n")
    before = _tree_snapshot(root)

    result = _evaluate_guard(root, record.record_id)

    assert result.status == "blocked"
    assert "record_receipt_mismatch" in result.blockers
    assert "canonical_source_digest_mismatch" in result.blockers
    assert _tree_snapshot(root) == before


def test_review_json_renderer_exposes_every_axis_and_receipt(tmp_path: Path):
    packet = _build_review(_release_repo(tmp_path))

    payload = json.loads(release.render_release_review_json(packet))

    assert payload["preview_receipt"] == packet.preview_receipt
    assert [axis["name"] for axis in payload["axes"]] == list(release.AXIS_NAMES)
    assert payload["research_only_boundary"] == release.RESEARCH_ONLY_BOUNDARY


def test_main_review_json_returns_zero_and_machine_readable_packet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    packet = _build_review(_release_repo(tmp_path))
    monkeypatch.setattr(release, "build_release_review", lambda *args, **kwargs: packet)

    status = release.main(["review", "--project-root", str(tmp_path), "--json"])
    captured = capsys.readouterr()

    assert status == 0
    assert json.loads(captured.out)["preview_receipt"] == packet.preview_receipt
    assert captured.err == ""


def test_main_record_validation_error_is_stable_and_traceback_free(capsys: pytest.CaptureFixture[str]):
    status = release.main(
        [
            "record",
            "--project-root",
            ".",
            "--preview-receipt",
            "invalid",
            "--reviewer",
            "Y. Jian",
            "--review-date",
            "2026-08-09",
            "--technical-decision",
            "approved",
            "--distribution-decision",
            "approved",
            "--confirm-reviewed",
        ]
    )
    captured = capsys.readouterr()

    assert status == 2
    assert captured.err.strip() == "readiness_release_error: invalid_preview_receipt"
    assert "Traceback" not in captured.err


def test_main_blocked_guard_returns_two(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    result = release.GuardResult(
        status="blocked",
        record_id="RRR-1",
        blockers=("distribution_decision_not_approved",),
        stage_paths=(),
        resume_command="make readiness-release-review TOP_N=20",
    )
    monkeypatch.setattr(release, "evaluate_guard", lambda *args, **kwargs: result)

    status = release.main(["guard", "--project-root", ".", "--record-id", "RRR-1"])
    captured = capsys.readouterr()

    assert status == 2
    assert "distribution_decision_not_approved" in captured.out
    assert captured.err == ""
