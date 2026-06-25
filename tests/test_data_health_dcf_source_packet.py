import pandas as pd

from src.data_health_dcf_source_packet import (
    dcf_proof_batch_planner_cards,
    dcf_proof_batch_planner_frame,
    dcf_source_packet_cards,
    dcf_source_packet_frame,
    fundamentals_batch_review_queue_frame,
)


def _dcf_queue_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": "META",
                "Missing Input Family": "shares_outstanding",
                "Missing DCF Fields": "shares_outstanding",
                "Source Mode": "SEC-stageable or trusted-local",
                "Validation Sequence": "make imports-validate -> make imports-preview -> rejected-row review -> make imports-apply",
                "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS=META",
                "Stop Rule": "Stop if shares_outstanding is unavailable from SEC/manual source proof.",
            },
            {
                "Ticker": "ACHV",
                "Missing Input Family": "fcf_margin",
                "Missing DCF Fields": "fcf_margin",
                "Source Mode": "trusted-local/manual",
                "Validation Sequence": "make imports-validate -> make imports-preview",
                "Proof Packet Command": "DRY_RUN=1 make fundamentals-batch-proof TICKERS=ACHV",
                "Stop Rule": "Stop if trusted source rows do not prove the required FCF margin field.",
            },
            {
                "Ticker": "AIAI",
                "Missing Input Family": "price",
                "Missing DCF Fields": "price",
                "Source Mode": "price refresh",
                "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=prices TICKERS=AIAI",
                "Stop Rule": "Stop if reviewed price rows are unavailable.",
            },
        ]
    )


def test_dcf_source_packet_groups_routes_without_hiding_blockers():
    packet = dcf_source_packet_frame(_dcf_queue_frame(), "All families")
    cards = dcf_source_packet_cards(_dcf_queue_frame(), "All families")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert packet["Source Route"].tolist() == ["SEC-stageable", "Trusted-local/manual", "Price dry-run path"]
    assert packet.loc[packet["Source Route"].eq("SEC-stageable"), "Stage Or Review Command"].iloc[0] == "make sec-stage TICKERS=META"
    assert packet.loc[packet["Source Route"].eq("Trusted-local/manual"), "Stage Or Review Command"].iloc[0] == "make dcf-input-source-review FAMILY=fcf_margin TOP_N=10"
    assert packet.loc[packet["Source Route"].eq("Price dry-run path"), "Stage Or Review Command"].iloc[0] == "DRY_RUN=1 make reviewed-batch LANE=prices TICKERS=AIAI"
    assert "choose sec staging only when configured and source-backed" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_fundamentals_batch_review_queue_keeps_validate_preview_apply_boundary():
    queue = fundamentals_batch_review_queue_frame(_dcf_queue_frame(), "All families", batch_size=1)
    table_text = " ".join(str(value) for value in queue.to_numpy().flatten()).lower()

    assert queue["Batch Route"].tolist() == ["SEC-stageable", "Trusted-local/manual", "Price dry-run path"]
    assert queue.loc[queue["Batch Route"].eq("SEC-stageable"), "Validation Gate"].iloc[0] == "make imports-validate IMPORT_TICKERS=META"
    assert queue.loc[queue["Batch Route"].eq("SEC-stageable"), "Preview Gate"].iloc[0] == "make imports-preview IMPORT_TICKERS=META"
    assert "review data/rejected/fundamentals_import_rejected.csv" in table_text
    assert "apply only reviewed sec/manual fundamentals rows after preview" in table_text
    assert "dry_run=1 make reviewed-batch-proof-record" in table_text


def test_dcf_proof_batch_planner_is_copy_only_and_stop_rule_first():
    planner = dcf_proof_batch_planner_frame(_dcf_queue_frame(), "shares_outstanding (1)")
    cards = dcf_proof_batch_planner_cards(_dcf_queue_frame(), "shares_outstanding (1)")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    table_text = " ".join(str(value) for value in planner.to_numpy().flatten()).lower()

    assert planner["Step"].tolist() == [
        "1. Choose DCF input family",
        "2. Review source route",
        "3. Preview reviewed batch packet",
        "4. Validate and preview",
        "5. Record proof only after review",
        "6. Stop rule",
    ]
    assert planner.loc[planner["Step"].eq("2. Review source route"), "Copy-Ready Action"].iloc[0] == "make sec-stage TICKERS=META"
    assert "packet preview is copy-only and does not make dcf-ready claims" in table_text
    assert "fill changed counts, changed tickers, source files" in table_text
    assert "do not write canonical fundamentals by default" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered
