import pandas as pd

from src.data_health_dcf_input_family import (
    dcf_input_family_filter_cards,
    dcf_input_family_key,
    dcf_input_family_options,
    dcf_input_rows_from_frame,
    filter_dcf_input_queue_by_family,
)


def _dcf_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Priority": 1,
                "Ticker": "AAA",
                "Scope": "active universe",
                "Missing Input Family": "shares_outstanding",
                "Missing DCF Fields": "shares_outstanding",
                "Ready DCF Inputs": "price, revenue, free_cash_flow",
                "DCF Input Status": "share count blocker",
                "Source Mode": "SEC-stageable",
                "Next Proof Command": "make focus-fundamentals TICKER=AAA",
                "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=share_count TOP_N=10",
                "Validation Sequence": "make imports-validate -> make imports-preview",
                "Proof After Update": "make dcf-readiness && make readiness",
                "Stop Rule": "Stop if share count proof is unavailable.",
                "Source Note": "Use source-backed share count only.",
            },
            {
                "Priority": 2,
                "Ticker": "BBB",
                "Scope": "active universe",
                "Missing Input Family": "fcf_margin",
                "Missing DCF Fields": "fcf_margin",
                "Ready DCF Inputs": "price, shares_outstanding",
                "DCF Input Status": "margin blocker",
                "Source Mode": "trusted-local",
                "Next Proof Command": "make focus-fundamentals TICKER=BBB",
                "Proof Packet Command": "DRY_RUN=1 make fundamentals-batch-proof TOP_N=10",
                "Validation Sequence": "make imports-validate -> make imports-preview",
                "Proof After Update": "make dcf-readiness && make readiness",
                "Stop Rule": "Stop if FCF margin proof is unavailable.",
                "Source Note": "Use source-backed FCF margin only.",
            },
            {
                "Priority": 3,
                "Ticker": "CCC",
                "Scope": "active universe",
                "Missing Input Family": "shares_outstanding",
                "Missing DCF Fields": "shares_outstanding",
                "Ready DCF Inputs": "price",
                "DCF Input Status": "share count blocker",
                "Source Mode": "SEC-stageable",
                "Next Proof Command": "make focus-fundamentals TICKER=CCC",
                "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=share_count TOP_N=10",
                "Validation Sequence": "make imports-validate -> make imports-preview",
                "Proof After Update": "make dcf-readiness && make readiness",
                "Stop Rule": "Stop if share count proof is unavailable.",
                "Source Note": "Use source-backed share count only.",
            },
        ]
    )


def test_dcf_input_family_helpers_filter_without_hiding_blockers():
    frame = _dcf_frame()

    options = dcf_input_family_options(frame)
    filtered = filter_dcf_input_queue_by_family(frame, "shares_outstanding (2)")
    all_rows = filter_dcf_input_queue_by_family(frame, "All families")
    cards = dcf_input_family_filter_cards(frame, filtered, "shares_outstanding (2)")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert options == ["All families", "shares_outstanding (2)", "fcf_margin (1)"]
    assert dcf_input_family_key("shares_outstanding (2)") == "shares_outstanding"
    assert len(filtered) == 2
    assert len(all_rows) == 3
    assert cards[0]["title"] == "shares_outstanding: 2 of 3"
    assert cards[0]["command"] == "make focus-fundamentals TICKER=AAA"
    assert "switch families to triage one proof lane at a time" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_dcf_input_rows_from_frame_preserves_source_and_proof_commands():
    rows = dcf_input_rows_from_frame(_dcf_frame())

    assert len(rows) == 3
    assert rows[0].ticker == "AAA"
    assert rows[0].missing_input_family == "shares_outstanding"
    assert rows[0].next_safe_command == "make focus-fundamentals TICKER=AAA"
    assert rows[0].proof_packet_command == "DRY_RUN=1 make reviewed-batch LANE=share_count TOP_N=10"
    assert rows[1].missing_input_family == "fcf_margin"


def test_dcf_input_family_empty_state_is_copy_only():
    cards = dcf_input_family_filter_cards(pd.DataFrame(), pd.DataFrame(), "All families")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "No proof-family rows loaded"
    assert cards[0]["command"] == "make dcf-input-proof-queue TOP_N=10"
    assert "blocked visible" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
