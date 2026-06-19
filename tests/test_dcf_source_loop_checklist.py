import pandas as pd

from src.data_health_dcf_source_commands import dcf_source_loop_checklist_cards, dcf_source_loop_checklist_frame


def _render(cards: list[dict[str, object]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_dcf_source_loop_checklist_blocks_on_placeholder_source_fields():
    selector = pd.DataFrame(
        {
            "Selected Count": [2],
            "Command Plan": ["make dcf-input-source-command-plan FAMILY=shares_outstanding TOP_N=2"],
        }
    )
    intake = pd.DataFrame(
        {
            "Reviewer Fill": ["<reviewed_source_file_or_url>", "<yyyy-mm-dd>"],
        }
    )
    readiness = pd.DataFrame(
        {
            "Guard Status": ["needs_field_fills"],
            "Missing Evidence Fields": ["source_file_or_url, source_as_of_date"],
            "Guard Command": ["Fill evidence fields before running dcf-input-source-guard."],
        }
    )

    frame = dcf_source_loop_checklist_frame(selector=selector, intake=intake, readiness=readiness)
    cards = dcf_source_loop_checklist_cards(frame, "shares_outstanding")
    rendered = _render(cards) + " " + " ".join(frame.astype(str).to_numpy().ravel().tolist()).lower()

    assert frame["Step"].tolist() == [
        "1. Select source-review batch",
        "2. Fill reviewed source fields",
        "3. Run source guard",
        "4. Validate and preview",
        "5. Apply, skip, or keep blocked",
        "6. Rebuild readiness and record proof",
    ]
    assert frame.iloc[0]["State"] == "ready"
    assert frame.iloc[1]["State"] == "needs_field_fills"
    assert "2 placeholder field(s)" in rendered
    assert "current gate: 2. fill reviewed source fields" in rendered
    assert "do not write canonical fundamentals" in rendered
    assert "no automatic apply from the dashboard" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_dcf_source_loop_checklist_keeps_apply_and_proof_manual_after_guard_ready():
    selector = pd.DataFrame({"Selected Count": [1], "Command Plan": ["make dcf-input-source-command-plan FAMILY=shares_outstanding TOP_N=1"]})
    intake = pd.DataFrame({"Reviewer Fill": ["10-K", "2026-03-31", "reviewed"]})
    readiness = pd.DataFrame(
        {
            "Guard Status": ["ready_for_guard"],
            "Missing Evidence Fields": ["-"],
            "Guard Command": ["make dcf-input-source-guard TICKER=AACB FAMILY=shares_outstanding"],
        }
    )
    preview = pd.DataFrame({"Guard Status": ["ready_for_guard"]})
    handoff = pd.DataFrame(
        {
            "Proof Handoff Status": ["ready_after_validate_preview_review"],
            "Missing Proof Fields": ["validation_result, preview_result, apply_result, changed_readiness_counts"],
            "Proof Record Dry Run": ["DRY_RUN=1 make reviewed-batch-proof-record TICKERS=AACB"],
        }
    )

    frame = dcf_source_loop_checklist_frame(
        selector=selector,
        intake=intake,
        readiness=readiness,
        preview=preview,
        handoff=handoff,
    )
    cards = dcf_source_loop_checklist_cards(frame, "shares_outstanding")
    rendered = _render(cards) + " " + " ".join(frame.astype(str).to_numpy().ravel().tolist()).lower()

    assert frame["State"].tolist() == [
        "ready",
        "ready",
        "ready",
        "ready",
        "manual_gate",
        "needs_reviewed_results",
    ]
    assert "current gate: 5. apply, skip, or keep blocked" in rendered
    assert "explicit apply/skip/still-blocked decision" in rendered
    assert "validation_result, preview_result, apply_result" in rendered
    assert "record proof only after rebuilt readiness" in rendered
    assert "canonical data changes require an explicit reviewed decision" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
