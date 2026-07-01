from pathlib import Path

import pandas as pd

from src import data_health_pilot_console as pilot_console


def _pilot_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Area": "GitHub sync",
                "Status": "green",
                "Gate": "GitHub branch state",
                "Detail": "main is synced.",
                "Command": "git status --short --branch",
                "Stop Rule": "Stop if the branch diverges.",
            },
            {
                "Area": "Generated artifact hygiene",
                "Status": "manual",
                "Gate": "Dirty tree classification",
                "Detail": "25 generated CSV artifacts are dirty and excluded by default.",
                "Command": "make diff-hygiene-summary",
                "Stop Rule": "Do not stage broad generated churn.",
            },
            {
                "Area": "Readiness freshness",
                "Status": "green",
                "Gate": "Readiness artifacts are current",
                "Detail": "Readiness artifacts are current.",
                "Command": "make status-check TOP_N=5",
                "Stop Rule": "Stop before quoting stale counts.",
            },
        ]
    )


def _proof_queue_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 3472,
                "Ready": 59,
                "Partial": 21,
                "Blocked": 3458,
                "Top Blockers": "fundamentals_bundle_plus_shares: 3459",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
                "Stop Rule": "Stop if revenue, free cash flow, FCF margin, or share-count proof is unavailable.",
            },
            {
                "Queue": "Peer Valuation Input Proof Queue",
                "State": "partial",
                "Queued Rows": 19,
                "Ready": 7,
                "Partial": 0,
                "Blocked": 19,
                "Top Blockers": "peer fundamentals: 19",
                "Next Safe Command": "make peer-mapping-queue TOP_N=25",
                "Stop Rule": "Stop if mapped peers lack trusted valuation-input rows.",
            },
        ]
    )


def test_pilot_cards_remain_copy_only_and_research_safe():
    cards = pilot_console.pilot_readiness_cards(_pilot_frame())
    packet = pilot_console.pilot_packet_cards(_pilot_frame(), output_path=Path("outputs/pilot_readiness_packet.md"))
    rendered = " ".join(str(card) for card in cards + packet).lower()

    assert cards[0]["title"] == "Pilot-ready with manual gates"
    assert "generated artifact hygiene" in rendered
    assert "outputs/pilot_readiness_packet.md" in rendered
    assert "does not refresh data or apply rows" in rendered
    assert "research-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pilot_reviewer_walkthrough_uses_deferred_proof_queue_when_fast_view():
    frame = pilot_console.pilot_reviewer_walkthrough_frame(_pilot_frame(), pd.DataFrame())
    cards = pilot_console.pilot_reviewer_walkthrough_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Stage"]) == [
        "Pilot status",
        "Manual gate to clear",
        "Source-proof focus",
        "Reviewer packet",
        "Public boundary",
    ]
    assert frame.iloc[1]["What Reviewer Sees"] == "Generated artifact hygiene"
    assert frame.iloc[2]["What Reviewer Sees"] == "Load source-proof queues"
    assert "switch readiness queue detail level to review details" in rendered
    assert "raw csv rows" in rendered
    assert "recommendation" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_pilot_reviewer_walkthrough_promotes_largest_source_proof_blocker():
    frame = pilot_console.pilot_reviewer_walkthrough_frame(_pilot_frame(), _proof_queue_frame())
    cards = pilot_console.pilot_reviewer_walkthrough_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    source_row = frame[frame["Stage"] == "Source-proof focus"].iloc[0]

    assert source_row["What Reviewer Sees"] == "Trusted Fundamentals Proof Queue"
    assert "3,458 blocked item" in source_row["Evidence"]
    assert "fundamentals_bundle_plus_shares" in source_row["Evidence"]
    assert source_row["Next Safe Action"] == "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10"
    assert "trusted fundamentals proof queue" in rendered
    assert "public-check" in rendered
    assert "broad generated churn stays excluded" in rendered


def test_pilot_reviewer_walkthrough_strip_is_compact_and_safe():
    frame = pilot_console.pilot_reviewer_walkthrough_frame(_pilot_frame(), _proof_queue_frame())
    html = pilot_console.pilot_reviewer_walkthrough_strip_html(frame)
    rendered = html.lower()

    assert "pilot-flow" in rendered
    assert "pilot workflow" in rendered
    assert "gate, proof focus, packet, and public-check before raw tables" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "make pilot-readiness-packet" in rendered
    assert "make public-check" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_operator_next_action_summary_answers_first_screen_questions():
    frame = pilot_console.operator_next_action_summary_frame(_pilot_frame(), _proof_queue_frame())
    cards = pilot_console.operator_next_action_summary_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Question"]) == [
        "Can this be piloted?",
        "What is the main manual gate?",
        "What blocks deeper analysis?",
        "What should stay hidden first?",
    ]
    assert frame.iloc[0]["Answer"] == "Pilot-ready with manual gates"
    assert frame.iloc[1]["Answer"] == "Generated artifact hygiene"
    assert frame.iloc[2]["Answer"] == "Trusted Fundamentals Proof Queue"
    assert frame.iloc[3]["Answer"] == "Raw tables and proof commands"
    assert "make dcf-input-source-command-plan" in rendered
    assert "validate, preview, rejected-row review" in rendered
    assert "copy-only" in rendered
    assert "research-only" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "advice" not in rendered


def test_operator_next_action_summary_deferred_state_stays_copy_only():
    frame = pilot_console.operator_next_action_summary_frame(_pilot_frame(), pd.DataFrame())
    cards = pilot_console.operator_next_action_summary_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert frame.iloc[2]["Answer"] == "Load source-proof queues"
    assert frame.iloc[2]["Status"] == "deferred"
    assert "review details before editing any data rows" in rendered
    assert "make data-coverage-proof-queues top_n=10" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_controlled_pilot_outcome_tracker_counts_reviewed_ticker_outcomes():
    ledger = pd.DataFrame(
        [
            {
                "Batch ID": "RB-1",
                "Lane": "fundamentals",
                "Tickers": "AAA",
                "Changed Tickers": "AAA",
                "Final Outcome": "supported",
                "Notes": "source-backed row reviewed",
            },
            {
                "Batch ID": "RB-2",
                "Lane": "share_count",
                "Tickers": "BBB",
                "Changed Tickers": "BBB",
                "Final Outcome": "still_blocked",
                "Notes": "explicit share-count proof unavailable",
            },
            {
                "Batch ID": "RB-3",
                "Lane": "peer_mapping",
                "Tickers": "CCC",
                "Changed Tickers": "",
                "Final Outcome": "candidate_context_only",
                "Notes": "candidate peers only",
            },
            {
                "Batch ID": "RB-4",
                "Lane": "fundamentals",
                "Tickers": "EEE",
                "Changed Tickers": "EEE",
                "Final Outcome": "skipped",
                "Notes": "not an operating company target",
            },
            {
                "Batch ID": "RB-5",
                "Lane": "fundamentals",
                "Tickers": "FFF",
                "Changed Tickers": "FFF",
                "Final Outcome": "excluded",
                "Notes": "not applicable",
            },
        ]
    )

    frame = pilot_console.controlled_pilot_outcome_frame(ledger)
    cards = pilot_console.controlled_pilot_outcome_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert frame.iloc[0]["Status"] == "pilot_exit_ready"
    assert frame.iloc[0]["Answer"] == "5 / 5 minimum reviewed ticker outcome(s)"
    assert "supported=1" in frame.iloc[1]["Evidence"]
    assert "candidate_context_only=1" in frame.iloc[1]["Evidence"]
    assert "still_blocked=1" in frame.iloc[1]["Evidence"]
    assert "skipped=1" in frame.iloc[1]["Evidence"]
    assert "excluded=1" in frame.iloc[1]["Evidence"]
    assert "controlled pilot can exit" in rendered
    assert "not a coverage unlock" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_controlled_pilot_outcome_tracker_stays_open_until_five_tickers():
    ledger = pd.DataFrame(
        [
            {"Batch ID": "RB-1", "Lane": "fundamentals", "Tickers": "AAA", "Final Outcome": "supported"},
            {"Batch ID": "RB-2", "Lane": "share_count", "Tickers": "BBB", "Final Outcome": "still_blocked"},
        ]
    )

    frame = pilot_console.controlled_pilot_outcome_frame(ledger)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert frame.iloc[0]["Status"] == "needs_more_packets"
    assert frame.iloc[0]["Answer"] == "2 / 5 minimum reviewed ticker outcome(s)"
    assert "run the next trusted-data pilot packet" in rendered
    assert "do not call unsupported lanes ready" in rendered


def test_controlled_pilot_outcome_tracker_ignores_broad_batch_records():
    ledger = pd.DataFrame(
        [
            {
                "Batch ID": "RB-PRICE-BROAD",
                "Lane": "prices",
                "Scope": "capped Yahoo missing-price refresh across remaining broad-universe price queue",
                "Tickers": "3289 changed tickers; sample A,AAL,AAME,AAON,ABBV",
                "Final Outcome": "supported",
            },
            {
                "Batch ID": "RB-OPTIONAL-BROAD",
                "Lane": "optional_context",
                "Scope": "all-universe optional context source ladder",
                "Tickers": "3538 tickers",
                "Final Outcome": "still_blocked",
            },
            {
                "Batch ID": "RB-A",
                "Lane": "fundamentals",
                "Scope": "one-company trusted-data pilot packet",
                "Tickers": "AAA",
                "Final Outcome": "supported",
            },
        ]
    )

    frame = pilot_console.controlled_pilot_outcome_frame(ledger)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert frame.iloc[0]["Status"] == "needs_more_packets"
    assert frame.iloc[0]["Answer"] == "1 / 5 minimum reviewed ticker outcome(s)"
    assert "ignored broad/non-pilot proof rows: 2" in rendered
    assert "aaa" in rendered
    assert "3289" not in frame.iloc[0]["Answer"]


def test_controlled_pilot_outcome_tracker_flags_oversized_historical_scope():
    ledger = pd.DataFrame(
        [
            {"Batch ID": f"RB-{i}", "Lane": "fundamentals", "Tickers": f"A{i:02d}", "Final Outcome": "supported"}
            for i in range(12)
        ]
    )

    frame = pilot_console.controlled_pilot_outcome_frame(ledger, target_min=5, target_max=10)
    cards = pilot_console.controlled_pilot_outcome_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert frame.iloc[0]["Status"] == "pilot_scope_review"
    assert frame.iloc[0]["Answer"] == "12 reviewed ticker outcome(s); select 5 to 10 for this pilot"
    assert "select a 5 to 10 company pilot set" in rendered
    assert "not a coverage unlock" in rendered


def test_pilot_evidence_review_combines_screenshots_packet_public_gate_and_churn():
    pilot_frame = pd.concat(
        [
            _pilot_frame(),
            pd.DataFrame(
                [
                    {
                        "Area": "Browser QA evidence",
                        "Status": "manual",
                        "Gate": "Public screenshot ready; workflow captures pending",
                        "Detail": "3 committed screenshot assets ready; pending workflow captures remain.",
                        "Command": "make browser-qa-evidence",
                        "Stop Rule": "Use real app screenshots only; do not use generated thumbnails.",
                    },
                    {
                        "Area": "Public safety",
                        "Status": "manual",
                        "Gate": "Run public-check",
                        "Detail": "Public-check remains the final share gate.",
                        "Command": "make public-check",
                        "Stop Rule": "Stop before public sharing if public-check fails.",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )

    frame = pilot_console.pilot_evidence_review_frame(
        pilot_frame,
        _proof_queue_frame(),
        output_path=Path("outputs/pilot_readiness_packet.md"),
    )
    cards = pilot_console.pilot_evidence_review_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Evidence Area"]) == [
        "Pilot verdict",
        "Screenshot evidence",
        "Pilot packet",
        "Public release gate",
        "Generated churn boundary",
        "Source-proof blocker",
    ]
    assert frame.iloc[1]["Next Safe Action"] == "make browser-qa-evidence"
    assert frame.iloc[2]["Review State"] == "outputs/pilot_readiness_packet.md"
    assert frame.iloc[3]["Next Safe Action"] == "make public-check"
    assert frame.iloc[4]["Next Safe Action"] == "make diff-hygiene-summary"
    assert frame.iloc[5]["Review State"] == "Trusted Fundamentals Proof Queue"
    assert "screenshots, packet, public gate, churn, and source proof in one place" in rendered
    assert "does not refresh data, apply imports" in rendered
    assert "generated thumbnails" in rendered
    assert "fundamentals_bundle_plus_shares" in rendered
    assert "blocked fundamentals, shares, market cap, peers" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_pilot_evidence_review_deferred_state_still_names_safe_commands():
    frame = pilot_console.pilot_evidence_review_frame(pd.DataFrame(), pd.DataFrame())
    cards = pilot_console.pilot_evidence_review_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert frame.iloc[0]["Review State"] == "Run pilot readiness check"
    assert frame.iloc[1]["Next Safe Action"] == "make browser-qa-evidence"
    assert frame.iloc[2]["Next Safe Action"] == "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md"
    assert frame.iloc[5]["Next Safe Action"] == "make data-coverage-proof-queues TOP_N=10"
    assert "run browser qa evidence" in rendered
    assert "generated csv/json/report churn stays excluded" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_public_share_final_gate_combines_release_checks_without_data_writes():
    pilot_frame = pd.concat(
        [
            _pilot_frame(),
            pd.DataFrame(
                [
                    {
                        "Area": "Browser QA evidence",
                        "Status": "manual",
                        "Detail": "3 committed screenshot assets ready; pending workflow captures remain.",
                        "Command": "make browser-qa-evidence",
                        "Stop Rule": "Use real app screenshots only.",
                    },
                    {
                        "Area": "Public safety",
                        "Status": "manual",
                        "Detail": "Public-check remains the explicit release gate.",
                        "Command": "make public-check",
                        "Stop Rule": "Stop if public-check fails.",
                    },
                    {
                        "Area": "Research guardrails",
                        "Status": "green",
                        "Detail": "Research-only boundary remains required.",
                        "Command": "make public-wording-check",
                        "Stop Rule": "Stop if wording becomes trade instructions.",
                    },
                ]
            ),
        ],
        ignore_index=True,
    )

    frame = pilot_console.public_share_final_gate_frame(
        pilot_frame,
        output_path=Path("outputs/pilot_readiness_packet.md"),
    )
    cards = pilot_console.public_share_final_gate_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Gate"]) == [
        "GitHub sync",
        "Public-check",
        "Browser QA evidence",
        "Generated churn exclusion",
        "Pilot packet",
        "License status",
        "Research-only boundary",
    ]
    assert frame.iloc[1]["Command"] == "make public-check"
    assert frame.iloc[2]["Command"] == "make browser-qa-evidence"
    assert frame.iloc[3]["Command"] == "make diff-hygiene-summary"
    assert frame.iloc[4]["Command"] == "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md"
    assert frame.iloc[5]["Command"] == "make license-status"
    assert frame.iloc[6]["Command"] == "make public-wording-check"
    assert "one final review before github or linkedin" in rendered
    assert "real screenshots" in rendered
    assert "generated-churn exclusion" in rendered
    assert "packet generation is read-only" in rendered
    assert "portfolio/demo only" in rendered
    assert "do not describe as open source" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_public_share_final_gate_deferred_state_names_all_release_gates():
    frame = pilot_console.public_share_final_gate_frame(pd.DataFrame())
    cards = pilot_console.public_share_final_gate_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert frame["Gate"].tolist() == [
        "GitHub sync",
        "Public-check",
        "Browser QA evidence",
        "Generated churn exclusion",
        "Pilot packet",
        "License status",
        "Research-only boundary",
    ]
    assert "git status --short --branch" in rendered
    assert "make public-check" in rendered
    assert "make browser-qa-evidence" in rendered
    assert "make diff-hygiene-summary" in rendered
    assert "make license-status" in rendered
    assert "portfolio/demo only" in rendered
    assert "make public-wording-check" in rendered
    assert "trade instructions" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_workflow_continuity_connects_evidence_queue_proof_and_artifacts():
    frame = pilot_console.data_health_workflow_continuity_frame(
        _pilot_frame(),
        _proof_queue_frame(),
        output_path=Path("outputs/pilot_readiness_packet.md"),
    )
    cards = pilot_console.data_health_workflow_continuity_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Step"]) == [
        "1. Evidence review",
        "2. Final share gate",
        "3. Next safe action",
        "4. Queue route map",
        "5. Proof lane",
        "6. Artifact hygiene",
        "7. Reviewer packet",
    ]
    assert frame.iloc[3]["Primary View"] == "Readiness queue review details"
    assert frame.iloc[3]["Next Safe Action"] == "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10"
    assert frame.iloc[4]["Route"] == "?mode=operator&page=data-health&lane=proof"
    assert frame.iloc[5]["Next Safe Action"] == "make diff-hygiene-summary"
    assert "one operator path, then drawers" in rendered
    assert "evidence review -> final share gate -> next action -> queue route map -> proof lane" in rendered
    assert "commands remain copy-only" in rendered
    assert "do not stage broad generated csv/json/report churn" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_data_health_workflow_continuity_deferred_state_keeps_safe_routes():
    frame = pilot_console.data_health_workflow_continuity_frame(pd.DataFrame(), pd.DataFrame())
    rendered = " ".join(frame.astype(str).to_numpy().ravel()).lower()

    assert "make pilot-readiness-check top_n=10" in rendered
    assert "make data-coverage-proof-queues top_n=10" in rendered
    assert "?mode=operator&page=data-health&lane=proof" in rendered
    assert "outputs/pilot_readiness_packet.md" in rendered
    assert "do not edit source rows" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
