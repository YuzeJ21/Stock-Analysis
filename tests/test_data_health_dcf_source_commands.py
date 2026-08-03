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
    dcf_source_guard_preview_cards,
    dcf_source_guard_preview_frame,
    dcf_source_guard_readiness_cards,
    dcf_source_guard_readiness_frame,
    dcf_source_loop_operator_summary_cards,
    dcf_source_loop_operator_summary_frame,
    dcf_source_proof_handoff_cards,
    dcf_source_proof_handoff_frame,
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


def test_dcf_source_guard_readiness_blocks_placeholder_evidence():
    intake = dcf_source_evidence_intake_frame([_row("META")], family="shares_outstanding", top_n=1)
    readiness = dcf_source_guard_readiness_frame(intake)
    cards = dcf_source_guard_readiness_cards(readiness, "shares_outstanding")
    rendered = " ".join(readiness.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert readiness.iloc[0]["Ticker"] == "META"
    assert readiness.iloc[0]["Guard Status"] == "needs_field_fills"
    assert "source_file_or_url" in readiness.iloc[0]["Missing Evidence Fields"]
    assert "shares_outstanding" in readiness.iloc[0]["Missing Evidence Fields"]
    assert readiness.iloc[0]["Guard Command"] == "Fill evidence fields before running dcf-input-source-guard."
    assert cards[0]["title"].startswith("shares_outstanding: needs field fills: 1")
    assert "run the guard only when every required evidence field is reviewed" in lowered
    assert "no placeholder proof" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_guard_readiness_builds_guard_command_when_evidence_is_filled():
    intake = dcf_source_evidence_intake_frame([_row("META")], family="shares_outstanding", top_n=1)
    replacements = {
        "source_file_or_url": "https://www.sec.gov/example",
        "source_as_of_date": "2026-06-01",
        "reviewer": "local_reviewer",
        "review_date": "2026-06-18",
        "source_proof_status": "reviewed",
        "shares_outstanding": "123456789",
    }
    intake["Reviewer Fill"] = intake["Evidence Field"].map(replacements).fillna(intake["Reviewer Fill"])

    readiness = dcf_source_guard_readiness_frame(intake)
    cards = dcf_source_guard_readiness_cards(readiness, "shares_outstanding")
    rendered = " ".join(readiness.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert readiness.iloc[0]["Guard Status"] == "ready_for_guard"
    assert readiness.iloc[0]["Missing Evidence Fields"] == "-"
    assert "make dcf-input-source-guard" in readiness.iloc[0]["Guard Command"]
    assert "TICKER=META" in readiness.iloc[0]["Guard Command"]
    assert "SHARES_OUTSTANDING=123456789" in readiness.iloc[0]["Guard Command"]
    assert cards[0]["command"].startswith("make dcf-input-source-guard")
    assert "ready for guard: 1" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_loop_operator_summary_shows_current_gate_before_tables():
    selector = dcf_source_batch_selector_frame([_row("META"), _row("ABNB")], family="shares_outstanding", top_n=2)
    intake = dcf_source_evidence_intake_frame([_row("META"), _row("ABNB")], family="shares_outstanding", top_n=2)
    readiness = dcf_source_guard_readiness_frame(intake)
    preview = dcf_source_guard_preview_frame(readiness)
    handoff = dcf_source_proof_handoff_frame(preview, "shares_outstanding")
    checklist = pd.DataFrame(
        [
            {
                "Step": "1. Select source-review batch",
                "State": "ready",
                "Next Safe Action": selector.iloc[0]["Command Plan"],
                "Missing Or Manual Gate": "-",
                "Review Boundary": "Use a capped source-review scope before opening raw DCF rows.",
            },
            {
                "Step": "2. Fill reviewed source fields",
                "State": "needs_field_fills",
                "Next Safe Action": "Fill reviewed source fields; do not write canonical fundamentals.",
                "Missing Or Manual Gate": "12 placeholder field(s)",
                "Review Boundary": "Evidence fields must be reviewed source values, not placeholders or inferred inputs.",
            },
        ]
    )

    summary = dcf_source_loop_operator_summary_frame(
        checklist,
        selector=selector,
        readiness=readiness,
        handoff=handoff,
        family="shares_outstanding",
    )
    cards = dcf_source_loop_operator_summary_cards(summary, "shares_outstanding")
    rendered = " ".join(summary.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert summary["Question"].tolist() == [
        "What is selected?",
        "What is the current gate?",
        "What does the guard say?",
        "When must I stop?",
    ]
    assert summary.iloc[0]["Status"] == "ready"
    assert "meta,abnb" in summary.iloc[0]["Answer"].lower()
    assert summary.iloc[1]["Status"] == "needs_field_fills"
    assert "current gate: 2. fill reviewed source fields" in summary.iloc[1]["Answer"].lower()
    assert "needs_field_fills: 2" in summary.iloc[2]["Answer"].lower()
    assert cards[0]["title"] == "shares_outstanding: needs_field_fills"
    assert "use this first-read summary before lower source tables" in lowered
    assert "no canonical fundamentals write" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_loop_operator_summary_marks_guard_ready_without_unlocking():
    selector = dcf_source_batch_selector_frame([_row("META")], family="shares_outstanding", top_n=1)
    intake = dcf_source_evidence_intake_frame([_row("META")], family="shares_outstanding", top_n=1)
    replacements = {
        "source_file_or_url": "https://www.sec.gov/example",
        "source_as_of_date": "2026-06-01",
        "reviewer": "local_reviewer",
        "review_date": "2026-06-18",
        "source_proof_status": "reviewed",
        "shares_outstanding": "123456789",
    }
    intake["Reviewer Fill"] = intake["Evidence Field"].map(replacements).fillna(intake["Reviewer Fill"])
    readiness = dcf_source_guard_readiness_frame(intake)
    preview = dcf_source_guard_preview_frame(readiness)
    handoff = dcf_source_proof_handoff_frame(preview, "shares_outstanding")
    checklist = pd.DataFrame(
        [
            {
                "Step": "1. Select source-review batch",
                "State": "ready",
                "Next Safe Action": selector.iloc[0]["Command Plan"],
                "Missing Or Manual Gate": "-",
                "Review Boundary": "Use a capped source-review scope before opening raw DCF rows.",
            },
            {
                "Step": "2. Fill reviewed source fields",
                "State": "ready",
                "Next Safe Action": "Fill reviewed source fields; do not write canonical fundamentals.",
                "Missing Or Manual Gate": "-",
                "Review Boundary": "Evidence fields must be reviewed source values, not placeholders or inferred inputs.",
            },
            {
                "Step": "6. Rebuild readiness and record proof",
                "State": "needs_reviewed_results",
                "Next Safe Action": handoff.iloc[0]["Proof Record Dry Run"],
                "Missing Or Manual Gate": handoff.iloc[0]["Missing Proof Fields"],
                "Review Boundary": "Record proof only after rebuilt readiness, changed counts, source files, and generated-artifact review.",
            },
        ]
    )

    summary = dcf_source_loop_operator_summary_frame(
        checklist,
        selector=selector,
        readiness=readiness,
        handoff=handoff,
        family="shares_outstanding",
    )
    rendered = " ".join(summary.astype(str).to_numpy().flatten().tolist()).lower()

    assert summary.iloc[2]["Status"] == "ready"
    assert "ready_for_guard: 1" in summary.iloc[2]["Answer"]
    assert "Proof handoff: ready_after_validate_preview_review: 1" in summary.iloc[2]["Answer"]
    assert "validation_result" in rendered
    assert "no supported proof outcome" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_source_guard_preview_blocks_until_guard_ready():
    intake = dcf_source_evidence_intake_frame([_row("META")], family="shares_outstanding", top_n=1)
    readiness = dcf_source_guard_readiness_frame(intake)
    preview = dcf_source_guard_preview_frame(readiness)
    cards = dcf_source_guard_preview_cards(preview, "shares_outstanding")
    rendered = " ".join(preview.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert preview.iloc[0]["Guard Status"] == "needs_field_fills"
    assert preview.iloc[0]["Validate"] == "blocked until guard readiness is ready_for_guard"
    assert preview.iloc[0]["Preview"] == "blocked until validation is reviewed"
    assert "do not apply imports while evidence fields are missing" in preview.iloc[0]["Apply Boundary"].lower()
    assert cards[0]["title"] == "shares_outstanding: 0 ready for guard"
    assert "missing evidence keeps the row blocked" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_guard_preview_shows_validate_preview_apply_boundary_when_ready():
    intake = dcf_source_evidence_intake_frame([_row("META")], family="shares_outstanding", top_n=1)
    replacements = {
        "source_file_or_url": "https://www.sec.gov/example",
        "source_as_of_date": "2026-06-01",
        "reviewer": "local_reviewer",
        "review_date": "2026-06-18",
        "source_proof_status": "reviewed",
        "shares_outstanding": "123456789",
    }
    intake["Reviewer Fill"] = intake["Evidence Field"].map(replacements).fillna(intake["Reviewer Fill"])
    readiness = dcf_source_guard_readiness_frame(intake)
    preview = dcf_source_guard_preview_frame(readiness)
    cards = dcf_source_guard_preview_cards(preview, "shares_outstanding")
    rendered = " ".join(preview.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert preview.iloc[0]["Guard Status"] == "ready_for_guard"
    assert preview.iloc[0]["Validate"] == "make imports-validate"
    assert preview.iloc[0]["Preview"] == "make imports-preview"
    assert "make imports-apply only after source guard" in preview.iloc[0]["Apply Boundary"]
    proof = preview.iloc[0]["Post-Guard Proof"]
    assert proof.startswith("make readiness-snapshot PROFILE=default && make dcf-readiness")
    assert "make reviewed-batch-compare PROFILE=default LANE=fundamentals" in proof
    assert proof.endswith("make stock-report-md TICKER=META")
    assert cards[0]["command"].startswith("make dcf-input-source-guard")
    assert "validate then preview" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered


def test_dcf_source_proof_handoff_blocks_until_guard_ready():
    intake = dcf_source_evidence_intake_frame([_row("META")], family="shares_outstanding", top_n=1)
    readiness = dcf_source_guard_readiness_frame(intake)
    preview = dcf_source_guard_preview_frame(readiness)
    handoff = dcf_source_proof_handoff_frame(preview, "shares_outstanding")
    cards = dcf_source_proof_handoff_cards(handoff, "shares_outstanding")
    rendered = " ".join(handoff.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert handoff.iloc[0]["Proof Handoff Status"] == "blocked_until_guard_ready"
    assert "guard_status" in handoff.iloc[0]["Missing Proof Fields"]
    assert handoff.iloc[0]["Proof Record Dry Run"] == "Finish evidence intake and source guard before proof-record dry run."
    assert cards[0]["command"] == "Finish evidence intake and source guard before proof-record dry run."
    assert "validation and preview stay blocked" in lowered
    assert "no generated artifacts are record-ready" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered
    assert "broker" not in lowered


def test_dcf_source_proof_handoff_builds_dry_run_record_scaffold_when_guard_ready():
    intake = dcf_source_evidence_intake_frame([_row("META")], family="shares_outstanding", top_n=1)
    replacements = {
        "source_file_or_url": "https://www.sec.gov/example",
        "source_as_of_date": "2026-06-01",
        "reviewer": "local_reviewer",
        "review_date": "2026-06-18",
        "source_proof_status": "reviewed",
        "shares_outstanding": "123456789",
    }
    intake["Reviewer Fill"] = intake["Evidence Field"].map(replacements).fillna(intake["Reviewer Fill"])
    readiness = dcf_source_guard_readiness_frame(intake)
    preview = dcf_source_guard_preview_frame(readiness)
    handoff = dcf_source_proof_handoff_frame(preview, "shares_outstanding")
    cards = dcf_source_proof_handoff_cards(handoff, "shares_outstanding")
    rendered = " ".join(handoff.astype(str).to_numpy().flatten().tolist()) + " " + _render_cards(cards)
    lowered = rendered.lower()

    assert handoff.iloc[0]["Proof Handoff Status"] == "ready_after_validate_preview_review"
    assert "validation_result" in handoff.iloc[0]["Missing Proof Fields"]
    assert "generated_artifacts_reviewed" in handoff.iloc[0]["Missing Proof Fields"]
    assert handoff.iloc[0]["Proof Record Dry Run"].startswith("DRY_RUN=1 make reviewed-batch-proof-record")
    assert "LANE=share_count" in handoff.iloc[0]["Proof Record Dry Run"]
    assert "VALIDATION_RESULT='<reviewed_validation_result>'" in handoff.iloc[0]["Proof Record Dry Run"]
    assert "SOURCE_FILES='<reviewed_source_files>'" in handoff.iloc[0]["Proof Record Dry Run"]
    assert "GENERATED_ARTIFACTS_REVIEWED='<kept_evidence_or_excluded_churn>'" in handoff.iloc[0]["Proof Record Dry Run"]
    assert cards[0]["command"].startswith("DRY_RUN=1 make reviewed-batch-proof-record")
    assert "not a recommendation" in lowered
    assert "buy now" not in lowered
    assert "sell now" not in lowered
    assert "broker" not in lowered
