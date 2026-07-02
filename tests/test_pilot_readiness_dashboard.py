import pandas as pd

from src.dashboard import (
    data_health_pilot_share_first_answer_frame,
    data_health_operator_next_action_summary_cards,
    data_health_operator_next_action_summary_frame,
    data_health_pilot_commit_package_cards,
    data_health_pilot_handoff_summary_cards,
    data_health_pilot_handoff_summary_frame,
    data_health_pilot_packet_cards,
    data_health_pilot_packaging_summary_cards,
    data_health_pilot_packaging_summary_frame,
    data_health_pilot_operator_runbook_cards,
    data_health_pilot_operator_runbook_frame,
    data_health_pilot_readiness_cards,
    data_health_pilot_reviewer_walkthrough_cards,
    data_health_pilot_reviewer_walkthrough_frame,
    data_health_pilot_reviewer_walkthrough_strip_html,
)


def test_data_health_pilot_readiness_cards_surface_verdict_and_priority_gates():
    frame = pd.DataFrame(
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
                "Status": "blocked",
                "Gate": "Readiness artifacts are stale",
                "Detail": "Run make readiness before relying on final counts.",
                "Command": "make readiness",
                "Stop Rule": "Stop before quoting final counts.",
            },
        ]
    )

    cards = data_health_pilot_readiness_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert cards[0]["title"] == "Blocked before pilot"
    assert "1 green gate" in cards[0]["body"]
    assert "1 manual gate" in cards[0]["body"]
    assert "1 blocked gate" in cards[0]["body"]
    assert cards[1]["title"] == "Readiness freshness"
    assert "make readiness" in rendered
    assert "generated artifact hygiene" in rendered
    assert "recommendation" not in rendered


def test_data_health_pilot_readiness_cards_empty_state_is_copy_only():
    cards = data_health_pilot_readiness_cards(pd.DataFrame())
    rendered = " ".join(str(card) for card in cards).lower()

    assert cards[0]["command"] == "make pilot-readiness-check TOP_N=10"
    assert "read-only" in rendered
    assert "pilot gate" in rendered


def test_data_health_pilot_packet_cards_are_copy_only_and_show_packet_path():
    frame = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "manual"},
            {"Area": "Research guardrails", "Status": "green"},
        ]
    )

    cards = data_health_pilot_packet_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert cards[0]["command"] == "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md"
    assert "outputs/pilot_readiness_packet.md" in rendered
    assert "does not refresh data or apply rows" in rendered
    assert "manual gates visible" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_pilot_handoff_summary_answers_reviewer_questions_before_tables():
    pilot = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "green", "Detail": "main is synced.", "Command": "git status --short --branch", "Stop Rule": "Stop if branch diverges."},
            {"Area": "Generated artifact hygiene", "Status": "manual", "Detail": "Generated churn is excluded.", "Command": "make diff-hygiene-summary", "Stop Rule": "Do not stage broad generated churn."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 100,
                "Blocked": 90,
                "Top Blockers": "fundamentals_bundle_plus_shares: 90",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
            }
        ]
    )

    frame = data_health_pilot_handoff_summary_frame(pilot, queues)
    cards = data_health_pilot_handoff_summary_cards(frame)
    rendered = " ".join(str(value) for value in frame.astype(str).to_numpy().ravel().tolist() + [str(card) for card in cards]).lower()

    assert frame["Question"].tolist() == [
        "Can this be shared as a pilot?",
        "What must be reviewed first?",
        "What blocks deeper analysis?",
        "What stays out of staging?",
        "What should the reviewer run next?",
    ]
    assert "pilot-ready with manual gates" in rendered
    assert "generated artifact hygiene" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "make pilot-readiness-packet output=outputs/pilot_readiness_packet.md" in rendered
    assert "read-only" in rendered
    assert "copy-only" in rendered
    assert "recommendation unlock" in rendered
    assert all(str(card["body"]).startswith("One answer:") for card in cards)
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_pilot_share_first_answer_frame_summarizes_release_gates():
    pilot = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "manual", "Detail": "## main...origin/main [ahead 3]", "Command": "git push origin main", "Stop Rule": "Do not push if generated churn is staged."},
            {"Area": "Generated artifact hygiene", "Status": "manual", "Detail": "35 generated artifact(s) excluded by default.", "Command": "make diff-hygiene-summary", "Stop Rule": "Do not stage broad generated churn."},
            {"Area": "Public safety", "Status": "manual", "Detail": "Run public-check before sharing.", "Command": "make public-check", "Stop Rule": "Stop if public-check fails."},
            {"Area": "Browser QA evidence", "Status": "green", "Detail": "Real screenshot evidence is ready.", "Command": "make browser-qa-evidence", "Stop Rule": "Stop if screenshots are stale."},
            {"Area": "License status", "Status": "manual", "Detail": "No root LICENSE file found.", "Command": "make license-status", "Stop Rule": "Do not claim reuse rights."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "reviewed",
                "Blocked": 90,
                "Top Blockers": "fundamentals_bundle_plus_shares: 90",
                "Next Safe Command": "make project-status",
            }
        ]
    )

    frame = data_health_pilot_share_first_answer_frame(pilot, queues)

    assert list(frame.columns) == ["Question", "Answer", "Share Boundary", "Next Safe Action"]
    assert frame.to_dict("records") == [
        {
            "Question": "Can I share this now?",
            "Answer": "Portfolio/demo only with manual gates; not open source and no reuse rights until a root LICENSE exists; 0 blocked gate(s), 4 manual gate(s), 1 green gate(s).",
            "Share Boundary": "Product evidence only; screenshots and packets do not prove data freshness or unlock blocked inputs.",
            "Next Safe Action": "make public-check",
        },
        {
            "Question": "What must be true first?",
            "Answer": "GitHub sync: manual; generated hygiene: manual; public-check: manual; browser evidence: green.",
            "Share Boundary": "Run share gates before posting the link; do not use them as analysis approval.",
            "Next Safe Action": "make public-check && make browser-qa-evidence",
        },
        {
            "Question": "What stays out?",
            "Answer": "35 generated artifact(s) excluded by default. License boundary: No root LICENSE file found.",
            "Share Boundary": "Generated churn, sample reports, and reuse claims stay out unless intentionally reviewed.",
            "Next Safe Action": "make diff-hygiene-summary",
        },
        {
            "Question": "What stays collapsed?",
            "Answer": "Release gate rows, proof queues, provider setup details, packet commands, and generated-artifact lists stay in review drawers until a reviewer opens them.",
            "Share Boundary": "The first answer stays share-focused; detailed evidence remains available but not first-screen noise.",
            "Next Safe Action": "Open the pilot/share evidence drawer only after the first answer is reviewed.",
        },
        {
            "Question": "What blocks deeper analysis?",
            "Answer": "Trusted Fundamentals Proof Queue: reviewed; fundamentals_bundle_plus_shares: 90.",
            "Share Boundary": "Source-proof blockers remain visible; sharing does not convert them into usable inputs.",
            "Next Safe Action": "make project-status",
        },
        {
            "Question": "What can change coverage next?",
            "Answer": "New source-backed rows, one configured keyed free-tier provider, reviewed manual rows, or changed blockers can reopen a narrow source-proof slice.",
            "Share Boundary": "Provider setup is not data proof; use one reviewed ticker smoke path before validate, preview, apply, or proof recording.",
            "Next Safe Action": "make provider-setup-checklist",
        },
        {
            "Question": "What should I review while queues are exhausted?",
            "Answer": "Choose a safe universe scope, then review risk context as historical context only; do not reopen broad proof loops from a stale blocker list.",
            "Share Boundary": "Scope and risk context do not infer missing fundamentals, peers, earnings, estimates, or valuation inputs.",
            "Next Safe Action": "make universe-scope TOP_N=10 && make risk-context",
        },
        {
            "Question": "What source preview can run safely?",
            "Answer": "Run the capped universe preview summary first; review SMH/S&P source warnings and row counts before any universe-stage or universe-apply step.",
            "Share Boundary": "Universe membership is metadata only; fallback holdings sources do not unlock fundamentals, share count, DCF, peers, earnings, estimates, or recommendations.",
            "Next Safe Action": "make universe-preview-summary",
        },
        {
            "Question": "What packet should I create?",
            "Answer": "outputs/pilot_readiness_packet.md is copy-only evidence; it does not refresh data or unlock blocked inputs.",
            "Share Boundary": "Packet is reviewer evidence only; it is not a release, data refresh, or proof apply step.",
            "Next Safe Action": "make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md",
        },
    ]


def test_data_health_pilot_handoff_summary_preserves_queue_priority_order():
    pilot = pd.DataFrame(
        [
            {"Area": "Source proof gates", "Status": "manual", "Command": "make data-coverage-proof-queues TOP_N=10", "Stop Rule": "Keep missing inputs visible."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "DCF Input Proof Batches",
                "State": "partial",
                "Blocked": 3458,
                "Queued Rows": 3477,
                "Top Blockers": "fundamentals_bundle_plus_shares: 3459",
                "Next Safe Command": "make dcf-input-proof-queue TOP_N=10",
            },
            {
                "Queue": "Peer Mapping Proof Queue",
                "State": "partial",
                "Blocked": 3512,
                "Queued Rows": 3512,
                "Top Blockers": "source-backed peer mappings: 3512",
                "Next Safe Command": "DRY_RUN=1 make peer-mapping-source-review TOP_N=10",
            },
        ]
    )

    frame = data_health_pilot_handoff_summary_frame(pilot, queues)
    blocker_row = frame.loc[frame["Question"].eq("What blocks deeper analysis?")].iloc[0]

    assert blocker_row["Answer"] == "DCF Input Proof Batches"
    assert blocker_row["Next Safe Action"] == "make dcf-input-proof-queue TOP_N=10"
    assert "3,458 blocked item" in blocker_row["Boundary"]


def test_data_health_pilot_commit_package_cards_keep_long_commands_secondary():
    frame = pd.DataFrame(
        [
            {
                "Step": "Stage reviewed product package",
                "Status": "ready_to_stage",
                "Copy-only Command": "git add -- README.md src/dashboard.py",
                "Boundary": "2 product/code/docs/test file(s) are eligible for staging. Review the diff first; do not use git add -A.",
            },
            {
                "Step": "Keep generated churn out",
                "Status": "excluded",
                "Copy-only Command": "make diff-hygiene-summary",
                "Boundary": "25 generated CSV/JSON/report artifact(s) remain excluded by default.",
            },
        ]
    )

    cards = data_health_pilot_commit_package_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert cards[0]["title"] == "Stage reviewed product package"
    assert cards[0]["command"] == "git add -- README.md src/dashboard.py"
    assert "ready to stage" in rendered
    assert "do not use git add -a" in rendered
    assert "generated csv/json/report artifact" in rendered
    assert "copy-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_pilot_reviewer_walkthrough_wraps_compact_path():
    pilot = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "green", "Detail": "main is synced.", "Command": "git status --short --branch", "Stop Rule": "Stop if branch diverges."},
            {"Area": "Generated artifact hygiene", "Status": "manual", "Detail": "Generated churn is excluded.", "Command": "make diff-hygiene-summary", "Stop Rule": "Do not stage broad generated churn."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 100,
                "Blocked": 90,
                "Top Blockers": "fundamentals_bundle_plus_shares: 90",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
                "Stop Rule": "Stop if source proof is unavailable.",
            }
        ]
    )

    frame = data_health_pilot_reviewer_walkthrough_frame(pilot, queues)
    cards = data_health_pilot_reviewer_walkthrough_cards(frame)
    strip = data_health_pilot_reviewer_walkthrough_strip_html(frame)
    rendered = " ".join(str(card) for card in cards).lower()
    rendered_strip = strip.lower()

    assert "one compact path before raw tables" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "make public-check" in rendered
    assert "copy-only" in rendered
    assert "pilot-flow" in rendered_strip
    assert "trusted fundamentals proof queue" in rendered_strip
    assert "make dcf-input-source-command-plan" in rendered_strip


def test_data_health_pilot_operator_runbook_wraps_share_and_source_gates():
    pilot = pd.DataFrame(
        [
            {"Area": "Public safety", "Status": "manual", "Detail": "Public-check remains required.", "Command": "make public-check", "Stop Rule": "Stop if public-check fails."},
            {"Area": "Browser QA evidence", "Status": "green", "Detail": "Real screenshots ready.", "Command": "make browser-qa-evidence", "Stop Rule": "Stop if screenshot evidence is stale."},
            {"Area": "Generated artifact hygiene", "Status": "manual", "Detail": "Generated churn excluded.", "Command": "make diff-hygiene-summary", "Stop Rule": "Do not stage broad generated churn."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "reviewed or exhausted",
                "Blocked": 90,
                "Top Blockers": "fundamentals_bundle_plus_shares: 90",
                "Next Safe Command": "make project-status",
                "Stop Rule": "Use provider setup before reopening proof queues.",
            }
        ]
    )

    frame = data_health_pilot_operator_runbook_frame(pilot, queues)
    cards = data_health_pilot_operator_runbook_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert frame["Step"].tolist() == [
        "1. Share gate",
        "2. Source gate",
        "3. Provider setup",
        "4. Reviewed one-ticker smoke command",
        "5. Validate / preview",
        "6. Packet and hygiene",
    ]
    assert "pilot operator runbook" in rendered
    assert "share-readiness, provider setup, and exhausted proof queues" in rendered
    assert "do not reopen broad proof loops" in rendered
    assert "make provider-setup-checklist" in rendered
    assert "make imports-validate import_tickers=<ticker>" in rendered


def test_data_health_pilot_packaging_summary_answers_share_gate_and_churn_boundary():
    pilot = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "green", "Detail": "main is synced.", "Command": "git status --short --branch", "Stop Rule": "Stop if branch diverges."},
            {"Area": "Generated artifact hygiene", "Status": "blocked", "Detail": "Product files are dirty.", "Command": "make diff-hygiene-summary", "Stop Rule": "Commit product files and exclude generated churn."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Blocked": 90,
                "Top Blockers": "fundamentals_bundle_plus_shares: 90",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
            }
        ]
    )

    frame = data_health_pilot_packaging_summary_frame(pilot, queues)
    cards = data_health_pilot_packaging_summary_cards(frame)
    rendered = " ".join(str(value) for value in frame.astype(str).to_numpy().ravel().tolist() + [str(card) for card in cards]).lower()

    assert frame["Review Question"].tolist() == [
        "Is this pilot shareable now?",
        "What blocks packaging?",
        "What blocks deeper analysis?",
        "What artifact can be reviewed?",
    ]
    assert "blocked before pilot" in rendered
    assert "generated artifact hygiene" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "outputs/pilot_readiness_packet.md" in rendered
    assert "broad generated csv/json/report churn stays excluded" in rendered
    assert "copy-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_data_health_operator_next_action_summary_wraps_first_screen_questions():
    pilot = pd.DataFrame(
        [
            {"Area": "GitHub sync", "Status": "green", "Detail": "main is synced.", "Command": "git status --short --branch", "Stop Rule": "Stop if branch diverges."},
            {"Area": "Generated artifact hygiene", "Status": "manual", "Detail": "Generated churn is excluded.", "Command": "make diff-hygiene-summary", "Stop Rule": "Do not stage broad generated churn."},
        ]
    )
    queues = pd.DataFrame(
        [
            {
                "Queue": "Trusted Fundamentals Proof Queue",
                "State": "partial",
                "Queued Rows": 100,
                "Blocked": 90,
                "Top Blockers": "fundamentals_bundle_plus_shares: 90",
                "Next Safe Command": "make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10",
                "Stop Rule": "Stop if source proof is unavailable.",
            }
        ]
    )

    frame = data_health_operator_next_action_summary_frame(pilot, queues)
    cards = data_health_operator_next_action_summary_cards(frame)
    rendered = " ".join(str(card) for card in cards).lower()

    assert list(frame["Question"]) == [
        "Can this be piloted?",
        "What is the main manual gate?",
        "What blocks deeper analysis?",
        "What should stay hidden first?",
    ]
    assert "pilot-ready with manual gates" in rendered
    assert "generated artifact hygiene" in rendered
    assert "trusted fundamentals proof queue" in rendered
    assert "raw tables and proof commands" in rendered
    assert "copy-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "advice" not in rendered
