import pandas as pd

from src.data_health_dcf_source_commands import (
    dcf_source_batch_selector_cards,
    dcf_source_batch_selector_frame,
    dcf_source_command_plan_cards,
    dcf_source_command_plan_frame,
    dcf_source_command_triage_cards,
    dcf_source_command_triage_frame,
    dcf_source_evidence_intake_cards,
    dcf_source_evidence_intake_frame,
)
from src.dcf_input_proof_queue import DcfInputProofRow


def _row(ticker: str = "META") -> DcfInputProofRow:
    return DcfInputProofRow(
        priority=1,
        ticker=ticker,
        scope="active universe",
        missing_input_family="shares_outstanding",
        missing_dcf_fields="shares_outstanding",
        ready_dcf_inputs="free_cash_flow, revenue, fcf_margin, price",
        dcf_input_status="single-input blocker: shares_outstanding",
        source_mode="SEC-stageable or trusted-local",
        next_safe_command=f"make share-count-proof-queue TICKERS={ticker}",
        proof_packet_command=f"DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS={ticker}",
        validation_sequence="make imports-validate -> make imports-preview -> rejected-row review -> make imports-apply",
        proof_after_update=f"make dcf-readiness && make readiness && make stock-report-md TICKER={ticker}",
        stop_rule="Stop if shares_outstanding is unavailable from SEC/manual source proof.",
        source_note="SEC staging is configured; use SEC/manual filing proof.",
    )


def _render_cards(cards: list[dict[str, object]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_dcf_source_command_plan_frame_and_cards_show_next_blocked_step():
    frame = dcf_source_command_plan_frame([_row()], "shares_outstanding")
    cards = dcf_source_command_plan_cards(frame, "shares_outstanding")
    rendered = " ".join(frame.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert frame["Step"].tolist() == [
        "1. Open source-review intake",
        "2. Fill and run source guard",
        "3. Validate import rows",
        "4. Preview import merge",
        "5. Apply boundary",
        "6. Rebuild DCF proof",
        "7. Proof handoff",
    ]
    assert cards[0]["title"] == "shares_outstanding: source review to proof handoff"
    assert cards[0]["command"] == "make dcf-input-source-command-plan FAMILY=shares_outstanding TOP_N=10"
    assert "next blocked step: 1. open source-review intake" in lowered
    assert "source_file_or_url" in lowered
    assert "make dcf-input-source-guard" in lowered
    assert "use this command path before opening raw source-review" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_command_plan_cards_empty_state_stays_blocked():
    cards = dcf_source_command_plan_cards(pd.DataFrame(), "shares_outstanding")
    rendered = _render_cards(cards)

    assert cards[0]["title"] == "No DCF source command plan available"
    assert cards[0]["command"] == "make dcf-input-proof-queue TOP_N=10"
    assert "refresh the dcf input queue" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_source_command_triage_summarizes_blocked_and_review_gates():
    plan = dcf_source_command_plan_frame([_row()], "shares_outstanding")
    triage = dcf_source_command_triage_frame(plan)
    cards = dcf_source_command_triage_cards(triage, "shares_outstanding")
    rendered = " ".join(triage.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert triage["Triage Bucket"].tolist() == [
        "needs_source_fields",
        "ready_for_guard_or_validate",
        "manual_apply_boundary",
        "proof_handoff_ready_after_review",
    ]
    assert triage.iloc[0]["Count"] == 2
    assert "source_file_or_url" in triage.iloc[0]["Review Boundary"]
    assert triage.iloc[0]["Next Safe Action"] == "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10"
    assert cards[0]["title"].startswith("shares_outstanding: needs source fields: 2")
    assert cards[0]["command"] == "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10"
    assert "next safest action" in lowered
    assert "fill fields, run the guard, validate/preview, or stop" in lowered
    assert "no fabricated unlocks" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_command_triage_empty_plan_uses_refresh_first_gate():
    triage = dcf_source_command_triage_frame(pd.DataFrame())
    cards = dcf_source_command_triage_cards(triage, "shares_outstanding")
    rendered = " ".join(triage.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert triage.iloc[0]["Triage Bucket"] == "blocked_no_plan"
    assert triage.iloc[0]["Next Safe Action"] == "make dcf-input-proof-queue TOP_N=10"
    assert cards[0]["command"] == "make dcf-input-proof-queue TOP_N=10"
    assert "refresh the dcf input queue" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_batch_selector_creates_capped_command_scope():
    rows = [_row("META"), _row("ABNB"), _row("HOOD")]
    selector = dcf_source_batch_selector_frame(rows, family="shares_outstanding", top_n=2)
    cards = dcf_source_batch_selector_cards(selector, "shares_outstanding")
    rendered = " ".join(selector.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert selector.iloc[0]["Batch Scope"] == "shares_outstanding: top 2"
    assert selector.iloc[0]["Selected Count"] == 2
    assert selector.iloc[0]["Tickers"] == "META,ABNB"
    assert selector.iloc[0]["Command Plan"] == "make dcf-input-source-command-plan FAMILY=shares_outstanding TICKERS=META,ABNB TOP_N=2"
    assert cards[0]["title"] == "shares_outstanding: 2 selected for source review"
    assert cards[0]["command"] == "make dcf-input-source-command-plan FAMILY=shares_outstanding TICKERS=META,ABNB TOP_N=2"
    assert "use this capped scope before opening raw dcf rows" in lowered
    assert "copy-only" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_batch_selector_blocks_empty_scope():
    selector = dcf_source_batch_selector_frame([], family="shares_outstanding", top_n=5)
    cards = dcf_source_batch_selector_cards(selector, "shares_outstanding")
    rendered = " ".join(selector.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert selector.iloc[0]["Triage Bucket"] == "blocked_no_rows"
    assert selector.iloc[0]["Command Plan"] == "make dcf-input-proof-queue TOP_N=10"
    assert cards[0]["command"] == "make dcf-input-proof-queue TOP_N=10"
    assert "do not build a source-review batch" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_evidence_intake_groups_reviewer_fields_before_csv_rows():
    intake = dcf_source_evidence_intake_frame([_row("META"), _row("ABNB")], family="shares_outstanding", top_n=2)
    cards = dcf_source_evidence_intake_cards(intake, "shares_outstanding")
    rendered = " ".join(intake.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert intake["Ticker"].nunique() == 2
    assert "source_file_or_url" in intake["Evidence Field"].tolist()
    assert "shares_outstanding" in intake["Evidence Field"].tolist()
    assert "<reviewed_shares_outstanding>" in intake["Reviewer Fill"].tolist()
    assert "sec filing" in lowered
    assert cards[0]["title"] == "shares_outstanding: 2 ticker(s), 12 evidence field(s)"
    assert cards[0]["command"] == "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10"
    assert "evidence before csv" in lowered
    assert "fill evidence fields before import rows" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_evidence_intake_empty_scope_stays_blocked():
    intake = dcf_source_evidence_intake_frame([], family="shares_outstanding", top_n=5)
    cards = dcf_source_evidence_intake_cards(intake, "shares_outstanding")
    rendered = " ".join(intake.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert intake.iloc[0]["Ticker"] == "<select_batch>"
    assert intake.iloc[0]["Reviewer Fill"] == "<run_dcf_input_proof_queue_first>"
    assert cards[0]["command"] == "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10"
    assert "do not fill evidence fields" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered
