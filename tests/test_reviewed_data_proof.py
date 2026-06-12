from pathlib import Path

from src.reviewed_data_proof import (
    ReviewedProof,
    append_reviewed_proof,
    lane_history_rows,
    load_reviewed_proofs,
    render_lane_outcome_history,
    render_price_reviewed_run_plan,
    render_public_demo_readiness_pack,
    render_reviewed_data_proofs,
)


def _proof(**overrides) -> ReviewedProof:
    values = {
        "proof_id": "RDP-TEST-001",
        "proof_date": "2026-06-12",
        "lane": "peer_valuation_inputs",
        "lane_label": "Peer valuation inputs proof path",
        "scope": "active-universe lane proof",
        "tickers_or_dependencies": "MU/TSLA dependencies: SNDK,F",
        "source_proof_status": "SEC Companyfacts source rows reviewed",
        "reviewer_outcome": "approved for reviewed import apply",
        "validate_result": "make imports-validate passed",
        "preview_result": "make imports-preview showed reviewed fundamentals changes",
        "apply_result": "make imports-apply applied reviewed fundamentals rows",
        "rejected_row_status": "rejected-row reports were clean",
        "readiness_before": "peer valuation inputs blocked by missing peer fundamentals",
        "readiness_after": "peer valuation inputs still blocked by mapped-peer price history",
        "final_outcome": "still_blocked",
        "changed_inputs": "reviewed SEC fundamentals for mapped-peer dependencies",
        "what_changed": "SEC-backed fundamentals for SNDK and F were added or refreshed",
        "still_blocked": "Mapped-peer price history remains missing for SNDK/F",
        "review_command": "make sec-stage TICKERS=F,SNDK",
        "proof_command": "make readiness && make peer-mapping-queue TOP_N=25",
        "artifact_paths": "data/fundamentals.csv",
        "generated_churn_policy": "keep broad generated CSV churn out of commits",
    }
    values.update(overrides)
    return ReviewedProof(**values)


def test_reviewed_proof_ledger_round_trips_and_renders_required_fields(tmp_path: Path):
    ledger = tmp_path / "reviewed_data_proofs.csv"
    append_reviewed_proof(_proof(), ledger)

    rows = load_reviewed_proofs(ledger)
    rendered = render_reviewed_data_proofs(rows)

    assert len(rows) == 1
    assert "Reviewed Data Proof Ledger" in rendered
    assert "source_proof_status: SEC Companyfacts source rows reviewed" in rendered
    assert "reviewer_outcome: approved for reviewed import apply" in rendered
    assert "validate/preview/apply: make imports-validate passed / make imports-preview showed reviewed fundamentals changes / make imports-apply applied reviewed fundamentals rows" in rendered
    assert "rejected_row_status: rejected-row reports were clean" in rendered
    assert "readiness before -> after: peer valuation inputs blocked by missing peer fundamentals -> peer valuation inputs still blocked by mapped-peer price history" in rendered
    assert "still_blocked" in rendered
    assert "proof rows do not provide investment advice, broker actions, or direct buy/sell instructions" in rendered


def test_lane_outcome_history_summarizes_without_generated_csv_churn():
    rows = [
        _proof(),
        _proof(
            proof_id="RDP-TEST-002",
            proof_date="2026-06-13",
            final_outcome="supported",
            still_blocked="No lane blocker remains after rebuilt readiness.",
        ),
    ]

    history = lane_history_rows(rows)
    rendered = render_lane_outcome_history(rows)

    assert history[0]["proof_count"] == "2"
    assert history[0]["latest_outcome"] == "supported"
    assert "outcome_mix: still_blocked: 1, supported: 1" in rendered
    assert "without reading generated readiness CSV churn" in rendered


def test_price_reviewed_run_plan_is_copy_only_with_snapshot_diff_and_rollback():
    rendered = render_price_reviewed_run_plan(max_candidates=3500, top_n=100, provider="yahoo", sleep_seconds=30)

    assert "Copy-only" in rendered
    assert "make readiness-snapshot" in rendered
    assert "make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo" in rendered
    assert "make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30" in rendered
    assert "make diff-hygiene" in rendered
    assert "Rollback notes:" in rendered
    assert "They do not create fundamentals, peers, earnings, estimates, valuation inputs, or recommendations" in rendered


def test_public_demo_readiness_pack_names_required_shareable_artifacts():
    rendered = render_public_demo_readiness_pack([_proof()])

    assert "Public Demo Readiness Pack" in rendered
    assert "`make dashboard` then open Home" in rendered
    assert "`make trusted-data-pilot-board` or dashboard `Data Health`" in rendered
    assert "`make stock-report-md TICKER=NVDA`" in rendered
    assert "`make stock-report-md TICKER=META`" in rendered
    assert "`make stock-report-md TICKER=QQQ`" in rendered
    assert "Latest reviewed proof: `RDP-TEST-001`" in rendered
