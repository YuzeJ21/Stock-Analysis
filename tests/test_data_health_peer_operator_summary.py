import pandas as pd

from src.data_health_peer_operator_summary import peer_operator_summary_cards, peer_operator_summary_frame
from src.peer_mapping_source_review import PeerMappingReviewRow, PeerMappingSourceReviewPacket
from src.reviewed_batch import FreshnessStatus


def _packet() -> PeerMappingSourceReviewPacket:
    return PeerMappingSourceReviewPacket(
        freshness=FreshnessStatus(status="current", message="readiness artifacts are current"),
        top_n=1,
        tickers=("META",),
        rows=(
            PeerMappingReviewRow(
                ticker="META",
                mapping_slot="peer_1",
                proposed_peer_ticker="<source-backed peer ticker>",
                peer_group="<reviewed peer group>",
                sector="<reviewed sector>",
                industry="<reviewed industry>",
                source="<durable URL or local document reference>",
                as_of_date="<YYYY-MM-DD>",
                relationship_rationale="<why this source supports the peer relationship>",
                reviewer="<reviewer>",
                review_date="<YYYY-MM-DD>",
                source_proof_status="needs_review",
                import_row_ready="no",
                target_file="data/imports/peers.csv",
                focus_command="make focus-peers TICKER=META",
                validation_sequence="make imports-validate -> make imports-preview -> make imports-apply",
                do_not_proceed_if="source does not name the peer relationship or comparable business context",
            ),
            PeerMappingReviewRow(
                ticker="META",
                mapping_slot="peer_2",
                proposed_peer_ticker="<source-backed peer ticker>",
                peer_group="<reviewed peer group>",
                sector="<reviewed sector>",
                industry="<reviewed industry>",
                source="<durable URL or local document reference>",
                as_of_date="<YYYY-MM-DD>",
                relationship_rationale="<why this source supports the peer relationship>",
                reviewer="<reviewer>",
                review_date="<YYYY-MM-DD>",
                source_proof_status="needs_review",
                import_row_ready="no",
                target_file="data/imports/peers.csv",
                focus_command="make focus-peers TICKER=META",
                validation_sequence="make imports-validate -> make imports-preview -> make imports-apply",
                do_not_proceed_if="source does not name the peer relationship or comparable business context",
            ),
        ),
    )


def test_peer_operator_summary_frame_keeps_missing_source_fields_visible():
    checklist = pd.DataFrame(
        [
            {
                "Checklist Item": "1. Confirm freshness and packet scope",
                "Status": "current",
                "Need Before Proceeding": "freshness current; tickers: META",
                "Next Safest Action": "DRY_RUN=1 make peer-mapping-source-review TOP_N=1",
                "Stop Rule": "Stop if readiness is stale or missing; do not use stale peer rows as proof.",
            },
            {
                "Checklist Item": "2. Fill peer source-review fields",
                "Status": "needs_field_fills",
                "Need Before Proceeding": "proposed_peer_ticker, peer_group, source",
                "Next Safest Action": "DRY_RUN=1 make peer-mapping-source-review TOP_N=1",
                "Stop Rule": "Stop if the source does not name the peer relationship or comparable business context.",
            },
        ]
    )
    outcome = pd.DataFrame(
        [
            {
                "Proof Loop Step": "Latest peer ledger outcome",
                "Status": "still_blocked",
                "Detail": "RB-PEERS; source rows still need review",
                "Next Safe Action": "make reviewed-batch-proof",
            }
        ]
    )

    summary = peer_operator_summary_frame(_packet(), checklist, outcome)
    cards = peer_operator_summary_cards(summary)
    rendered = " ".join(
        summary.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert summary["Question"].tolist() == [
        "What is selected?",
        "What is the current gate?",
        "What proof exists?",
        "When must I stop?",
    ]
    assert summary.iloc[0]["Answer"] == (
        "2 peer source-review slot(s); tickers: META. "
        "Candidate context: 0 candidate-only slot(s), 2 no-context slot(s)."
    )
    assert summary.iloc[1]["Status"] == "needs_field_fills"
    assert "proposed_peer_ticker" in summary.iloc[1]["Answer"]
    assert summary.iloc[2]["Status"] == "still_blocked"
    assert cards[0]["title"] == "Current gate: needs_field_fills"
    assert "use this first-read summary before lower peer source tables" in rendered
    assert "no peer-relative valuation unlock" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered
    assert "broker" not in rendered


def test_peer_operator_summary_separates_candidate_context_from_trusted_proof():
    packet = PeerMappingSourceReviewPacket(
        freshness=FreshnessStatus(status="current", message="readiness artifacts are current"),
        top_n=1,
        tickers=("ACGL",),
        rows=(
            PeerMappingReviewRow(
                ticker="ACGL",
                mapping_slot="peer_1",
                proposed_peer_ticker="<source-backed peer ticker>",
                peer_group="<reviewed peer group>",
                sector="<reviewed sector>",
                industry="<reviewed industry>",
                source="<durable URL or local document reference>",
                as_of_date="<YYYY-MM-DD>",
                relationship_rationale="<why this source supports the peer relationship>",
                reviewer="<reviewer>",
                review_date="<YYYY-MM-DD>",
                source_proof_status="needs_review",
                import_row_ready="no",
                target_file="data/imports/peers.csv",
                focus_command="make focus-peers TICKER=ACGL",
                validation_sequence="make imports-validate IMPORT_TICKERS=ACGL -> make imports-preview IMPORT_TICKERS=ACGL",
                do_not_proceed_if="source does not name the peer relationship or comparable business context",
                candidate_context_state="candidate_context_only",
                candidate_context_source="source_detail_fallback",
                candidate_context_count="75",
                candidate_context_peers="AFL, AIG, AIZ",
                candidate_context_note="Candidate context only from local classification fallback; not trusted peer proof.",
            ),
        ),
    )

    summary = peer_operator_summary_frame(packet, pd.DataFrame(), pd.DataFrame())
    cards = peer_operator_summary_cards(summary)
    rendered = " ".join(
        summary.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert "Candidate context: 1 candidate-only slot(s), 0 no-context slot(s)." in summary.iloc[0]["Answer"]
    assert "trusted peers require reviewed source-backed rows" in summary.iloc[0]["Boundary"]
    assert "candidate context can route review work" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_peer_operator_summary_missing_packet_blocks_first():
    summary = peer_operator_summary_frame(None, pd.DataFrame(), pd.DataFrame())
    cards = peer_operator_summary_cards(summary)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert summary.iloc[0]["Status"] == "missing_packet"
    assert summary.iloc[0]["Next Safe Action"] == "make readiness-preview TOP_N=20"
    assert cards[0]["command"] == "make readiness-preview TOP_N=20"
    assert "does not refresh or persist saved readiness" in rendered
    assert "inspect missing readiness" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered
