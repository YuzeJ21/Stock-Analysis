import pandas as pd

from src.data_health_coverage_proof_summary import data_coverage_proof_queue_cards, fundamentals_peer_metrics_queue_cards


def test_fundamentals_peer_metrics_queue_cards_keep_next_layer_scan_friendly():
    frame = pd.DataFrame(
        [
            {
                "Lane": "Fundamentals / DCF Proof",
                "State": "partial",
                "Partial": 12,
                "Blocked": 3458,
                "Missing Input Families": "trusted fundamentals, dated revenue, free cash flow, FCF margin",
                "Source Mode": "SEC-stageable or trusted-local",
                "Next Safe Command": "make sec-stage-queue TOP_N=25",
                "Proof Gate": "Validate -> preview -> rejected-row review -> apply only reviewed trusted rows -> rebuild readiness.",
            },
            {
                "Lane": "Metrics Readiness",
                "State": "partial",
                "Partial": 10,
                "Blocked": 2,
                "Missing Input Families": "benchmark / risk: 2",
                "Source Mode": "local_readiness",
                "Next Safe Command": "make metric-readiness-board TOP_N=10",
                "Proof Gate": "SPY/QQQ review metrics stay gated by trusted local inputs.",
            },
        ]
    )

    cards = fundamentals_peer_metrics_queue_cards(frame, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    body_rendered = " ".join(str(card["body"]) for card in cards).lower()

    assert cards[0]["title"] == "What can I use by lane?"
    assert cards[1]["title"] == "Fundamentals / DCF Proof"
    assert cards[2]["title"] == "Metrics Readiness"
    assert cards[1]["command"] == "make sec-stage-queue TOP_N=25"
    assert cards[2]["command"] == "make metric-readiness-board TOP_N=10"
    assert "one answer per lane" in rendered
    assert "usable now:" in rendered
    assert "partly usable; ready rows can support research context, locked fields stay blocked" in rendered
    assert "blocked by: trusted fundamentals" in rendered
    assert "next: open the evidence drawer" in rendered
    assert "make " not in body_rendered
    assert "trusted fundamentals" in rendered
    assert "spy/qqq review metrics" in rendered
    assert "readiness first" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_data_coverage_proof_queue_cards_keep_batch_path_compact_and_copy_only():
    frame = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 3472,
                "Top Blockers": "fundamentals_bundle_plus_shares: 3459",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
                "Stop Rule": "Stop if revenue, free cash flow, FCF margin, or share-count proof is unavailable.",
            },
            {
                "Queue": "Peer Mapping Proof Queue",
                "State": "still_blocked",
                "Queued Rows": 3512,
                "Top Blockers": "source-backed peer mappings: 3512",
                "Next Safe Command": "DRY_RUN=1 make peer-mapping-source-review TOP_N=10",
                "Stop Rule": "Stop if peer rows are guessed, self-peers, duplicates, undocumented, or stale.",
            },
        ]
    )

    cards = data_coverage_proof_queue_cards(frame, limit=2)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Proof queues before row work"
    assert cards[1]["title"] == "Peer Mapping Proof Queue"
    assert cards[2]["title"] == "Trusted Fundamentals Proof Queue"
    assert "3,512 queued row" in rendered
    assert "3,472 queued row" in rendered
    assert "source proof first" in rendered
    assert "copy-only commands" in rendered
    assert "dry_run=1 make peer-mapping-source-review" in rendered
    assert "make dcf-input-source-command-plan" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_data_coverage_proof_queue_cards_surface_reviewed_status_before_repeating_queue():
    frame = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 333,
                "Top Blockers": "fundamentals_bundle: 242; fundamentals_bundle_plus_shares: 91",
                "Next Safe Command": "make project-status",
                "Stop Rule": "Do not repeat source ladder loops without new source-backed rows.",
                "Reviewed Proof Status": (
                    "current DCF/share-count source ladder has only reviewed non-actionable blockers; "
                    "wait for new provider data, keyed sources, or reviewed manual source rows before repeating this proof loop."
                ),
            }
        ]
    )

    cards = data_coverage_proof_queue_cards(frame, limit=1)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[1]["command"] == "make project-status"
    assert "reviewed proof status:" in rendered
    assert "reviewed non-actionable blockers" in rendered
    assert "do not repeat the proof queue" in rendered
    assert "333 queued row" not in rendered
    assert "source gate" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_data_coverage_proof_queue_cards_start_with_source_gate_when_all_visible_queues_reviewed():
    frame = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 333,
                "Top Blockers": "fundamentals_bundle: 242",
                "Next Safe Command": "make project-status",
                "Stop Rule": "Do not repeat source ladder loops without new source-backed rows.",
                "Reviewed Proof Status": "current source ladder has only reviewed non-actionable blockers.",
            },
            {
                "Queue": "Peer Mapping Proof Queue",
                "State": "still_blocked",
                "Queued Rows": 3507,
                "Top Blockers": "source-backed peer mappings: 3507",
                "Next Safe Command": "make project-status",
                "Stop Rule": "Do not repeat peer loops without new source-backed rows.",
                "Reviewed Proof Status": "reviewed proof ledger covers the current peer mapping scope.",
            },
        ]
    )

    cards = data_coverage_proof_queue_cards(frame, limit=2)
    rendered_first = " ".join(str(value) for value in cards[0].values()).lower()

    assert cards[0]["title"] == "Source gate before proof queues"
    assert cards[0]["command"] == "make project-status"
    assert "reviewed or exhausted" in rendered_first
    assert "provider setup" in rendered_first
    assert "data-coverage-proof-queues" not in rendered_first
    assert "buy" not in rendered_first
    assert "sell" not in rendered_first
    assert "broker" not in rendered_first


def test_data_coverage_proof_queue_cards_empty_state_keeps_blockers_visible():
    cards = data_coverage_proof_queue_cards(pd.DataFrame())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards == [
        {
            "kicker": "PROOF QUEUES",
            "title": "Run readiness before proof queue review",
            "body": "DCF, shares, fundamentals, peer mapping, and peer valuation proof queues need saved readiness artifacts.",
            "badges": ["read-only", "blocked visible"],
            "command": "make data-coverage-proof-queues TOP_N=10",
        }
    ]
    assert "blocked visible" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
