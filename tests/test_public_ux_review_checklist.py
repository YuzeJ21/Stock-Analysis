from src.public_ux_review_checklist import (
    PUBLIC_ROUTES,
    public_ux_review_payload,
    public_ux_review_notes_status,
    main,
    record_public_ux_review_note,
    render_public_ux_review_checklist,
    render_public_ux_review_notes,
    render_public_ux_review_notes_status,
    write_public_ux_review_notes,
)


def test_public_ux_review_checklist_is_read_only_and_route_complete():
    rendered = render_public_ux_review_checklist()

    assert "Public UX Review Checklist" in rendered
    assert "does not refresh data, import rows, capture screenshots, stage files, commit, or push" in rendered
    assert "product QA, not investment advice, broker integration, data freshness proof, or trade instruction" in rendered
    assert len(PUBLIC_ROUTES) == 5
    for page in ("Home", "Stock Selector", "Single-Stock Report", "Data Health", "Proof History"):
        assert f"| {page} |" in rendered
    assert "http://localhost:8501/?mode=public&page=stock-selector" in rendered
    assert "http://localhost:8501/?mode=public&page=single-stock-report&ticker=NVDA&open=1" in rendered
    assert "http://localhost:8501/?mode=public&page=data-health" in rendered
    assert "http://localhost:8501/?mode=public&page=proof-history" in rendered
    assert "Page question" in rendered
    assert "If it fails" in rendered
    assert "Responsive route checks:" in rendered
    assert "Desktop viewport" in rendered
    assert "Phone viewport" in rendered
    assert "390x844" in rendered
    assert "What is this product and where do I start?" in rendered
    assert "Which stock can I review?" in rendered
    assert "What can I use for this ticker right now?" in rendered
    assert "Why is something blocked and how do I fix it?" in rendered
    assert "What evidence changed a readiness state?" in rendered
    assert "Coverage Summary / What Can I Use?" in rendered
    assert "Evidence-only page, latest proof outcome, raw ledger details collapsed" in rendered


def test_public_ux_review_checklist_keeps_operator_details_and_data_claims_out():
    rendered = render_public_ux_review_checklist()

    assert "one question, one short answer, one primary next action, and one stop rule" in rendered
    assert "Desktop and mobile review rules:" in rendered
    assert "Confirm the visible page question matches the route's job in the table above." in rendered
    assert "If the page fails, fix only the matching failure action before adding new sections or routes." in rendered
    assert "raw tables, command blocks, proof ledgers, provider setup, and operator evidence stay behind Advanced or operator mode" in rendered
    assert "Stop if mobile hides the selector, shows raw readiness tables first, or forces horizontal scrolling." in rendered
    assert "Stop if provider setup, operator commands, raw tables, or proof ledgers appear before the coverage answer." in rendered
    assert "Confirm screenshots remain product evidence only and do not claim data freshness." in rendered
    assert "Browser capture fallback:" in rendered
    assert "If in-app browser capture is unavailable or times out, classify the review as environment_limited" in rendered
    assert "Do not replace screenshot assets from a timed-out, blank, cropped, or loading capture." in rendered
    assert "Review log template:" in rendered
    assert "Issue classification: resolved, intentionally_deferred, environment_limited, skipped, or blocked_with_evidence" in rendered
    assert "blocked, candidate-only, skipped, or excluded lane appears as analysis-ready" in rendered
    assert "broker trading, order routing, auto-trading, direct buy/sell instructions, or investment advice" in rendered
    assert "make project-status-check" in rendered
    assert "make public-check" in rendered
    assert "make diff-hygiene-summary" in rendered


def test_public_ux_review_payload_is_machine_readable_for_long_runs():
    payload = public_ux_review_payload()

    assert payload["title"] == "Public UX Review Checklist"
    assert payload["mode"] == "read_only_product_qa"
    assert payload["public_workflow"] == [
        "Home",
        "Stock Selector",
        "Single-Stock Report",
        "Data Health",
        "Proof History",
    ]
    assert len(payload["route_checks"]) == 5
    assert payload["route_checks"][0]["page"] == "Home"
    assert payload["route_checks"][0]["question"] == "What is this product and where do I start?"
    assert payload["responsive_route_checks"][0]["Desktop Viewport"] == "1280x720"
    assert payload["responsive_route_checks"][0]["Phone Viewport"] == "390x844"
    assert "environment_limited" in payload["browser_capture_fallback"][0]
    assert "Do not replace screenshot assets" in payload["browser_capture_fallback"][2]
    assert payload["review_note_artifact"]["suggested_local_folder"] == "/tmp/stock-command-center-public-ux-review"
    assert payload["review_note_artifact"]["suggested_notes_file"] == "public-ux-review-notes.md"
    assert payload["review_note_artifact"]["git_boundary"] == "local audit notes only; do not stage unless intentionally reviewed"
    assert payload["live_review_protocol"][0] == "Create the suggested local audit folder before opening routes."
    assert "environment_limited" in payload["live_review_protocol"][-1]
    assert payload["next_safe_commands"] == [
        "make dashboard",
        "make public-ux-review-checklist-json",
        "make public-ux-review-notes-check",
        "make project-status-check",
        "make dashboard-smoke",
        "make browser-qa-evidence",
        "make public-check",
        "make diff-hygiene-summary",
    ]


def test_public_ux_review_checklist_prints_review_note_artifact():
    rendered = render_public_ux_review_checklist()

    assert "Review note artifact:" in rendered
    assert "- Suggested local folder: /tmp/stock-command-center-public-ux-review" in rendered
    assert "- Suggested notes file: public-ux-review-notes.md" in rendered
    assert "- Git boundary: local audit notes only; do not stage unless intentionally reviewed" in rendered
    assert "Live review protocol:" in rendered
    assert "- Record one note row per page/viewport before changing code or screenshots." in rendered
    assert "- If capture is environment_limited, record that state once and continue with repo-side checks." in rendered


def test_public_ux_review_notes_template_is_share_safe_and_route_complete(tmp_path):
    rendered = render_public_ux_review_notes()

    assert "# Public UX Review Notes" in rendered
    assert "Research-only product QA notes; not investment advice, data freshness proof, or trade instruction." in rendered
    assert "Screenshots remain product evidence only and do not unlock blocked inputs." in rendered
    assert "| Page | Viewport | First answer visible | Primary next action visible | Advanced/raw details collapsed | Issue classification | Notes |" in rendered
    for page in ("Home", "Stock Selector", "Single-Stock Report", "Data Health", "Proof History"):
        assert f"| {page} | desktop |" in rendered
        assert f"| {page} | phone |" in rendered
    assert "environment_limited" in rendered
    assert "Do not stage this file unless it is intentionally reviewed as pilot evidence." in rendered

    output_path = write_public_ux_review_notes(tmp_path)

    assert output_path == tmp_path / "public-ux-review-notes.md"
    assert output_path.read_text(encoding="utf-8") == rendered + "\n"


def test_public_ux_review_notes_status_reports_missing_template(tmp_path):
    missing_path = tmp_path / "missing.md"

    status = public_ux_review_notes_status(missing_path)
    rendered = render_public_ux_review_notes_status(missing_path)

    assert status["status"] == "notes_missing"
    assert status["path"] == str(missing_path)
    assert status["pending_rows"] == 10
    assert status["next_safe_command"] == "make public-ux-review-notes"
    assert status["next_pending_review"]["page"] == "Home"
    assert status["next_pending_review"]["viewport"] == "desktop"
    assert status["next_pending_review"]["route"] == "http://localhost:8501/?mode=public"
    assert "Public UX Review Notes Status" in rendered
    assert "notes_missing" in rendered
    assert "make public-ux-review-notes" in rendered
    assert "next_pending_review: Home | desktop | http://localhost:8501/?mode=public" in rendered


def test_public_ux_review_notes_status_counts_pending_and_reviewed_rows(tmp_path):
    notes_path = write_public_ux_review_notes(tmp_path)
    text = notes_path.read_text(encoding="utf-8")
    text = text.replace(
        "| Home | desktop | pending | pending | pending | pending |  |",
        "| Home | desktop | yes | yes | yes | resolved | Looks clear. |",
    )
    text = text.replace(
        "| Data Health | phone | pending | pending | pending | pending |  |",
        "| Data Health | phone | no | yes | no | environment_limited | Browser capture timed out; use normal browser. |",
    )
    notes_path.write_text(text, encoding="utf-8")

    status = public_ux_review_notes_status(notes_path)
    rendered = render_public_ux_review_notes_status(notes_path)

    assert status["status"] == "review_in_progress"
    assert status["total_rows"] == 10
    assert status["pending_rows"] == 8
    assert status["classification_counts"]["resolved"] == 1
    assert status["classification_counts"]["environment_limited"] == 1
    assert status["classification_counts"]["pending"] == 8
    assert status["next_pending_review"]["page"] == "Home"
    assert status["next_pending_review"]["viewport"] == "phone"
    assert status["next_pending_review"]["route"] == "http://localhost:8501/?mode=public"
    assert status["problem_rows"] == [
        {
            "page": "Data Health",
            "viewport": "phone",
            "classification": "environment_limited",
            "notes": "Browser capture timed out; use normal browser.",
        }
    ]
    assert "review_in_progress" in rendered
    assert "pending: 8" in rendered
    assert "environment_limited: 1" in rendered
    assert "next_pending_review: Home | phone | http://localhost:8501/?mode=public" in rendered
    assert "Data Health | phone | environment_limited" in rendered


def test_record_public_ux_review_note_updates_one_row_and_advances_queue(tmp_path):
    notes_path = write_public_ux_review_notes(tmp_path)

    updated_path = record_public_ux_review_note(
        notes_path=notes_path,
        page="Home",
        viewport="desktop",
        first_answer_visible="yes",
        primary_next_action_visible="yes",
        advanced_details_collapsed="yes",
        classification="resolved",
        notes="First viewport is clear.",
    )

    assert updated_path == notes_path
    text = notes_path.read_text(encoding="utf-8")
    assert "| Home | desktop | yes | yes | yes | resolved | First viewport is clear. |" in text
    assert "| Home | phone | pending | pending | pending | pending |  |" in text

    status = public_ux_review_notes_status(notes_path)

    assert status["pending_rows"] == 9
    assert status["classification_counts"]["resolved"] == 1
    assert status["next_pending_review"]["page"] == "Home"
    assert status["next_pending_review"]["viewport"] == "phone"


def test_record_public_ux_review_note_defaults_to_next_pending_row(tmp_path):
    notes_path = write_public_ux_review_notes(tmp_path)
    record_public_ux_review_note(
        notes_path=notes_path,
        page="Home",
        viewport="desktop",
        first_answer_visible="yes",
        primary_next_action_visible="yes",
        advanced_details_collapsed="yes",
        classification="resolved",
        notes="Desktop reviewed.",
    )

    record_public_ux_review_note(
        notes_path=notes_path,
        page=None,
        viewport=None,
        first_answer_visible="yes",
        primary_next_action_visible="yes",
        advanced_details_collapsed="yes",
        classification="resolved",
        notes="Defaulted to next pending row.",
    )

    text = notes_path.read_text(encoding="utf-8")
    status = public_ux_review_notes_status(notes_path)

    assert "| Home | phone | yes | yes | yes | resolved | Defaulted to next pending row. |" in text
    assert status["pending_rows"] == 8
    assert status["next_pending_review"]["page"] == "Stock Selector"
    assert status["next_pending_review"]["viewport"] == "desktop"


def test_record_public_ux_review_note_rejects_unknown_page(tmp_path):
    notes_path = write_public_ux_review_notes(tmp_path)

    try:
        record_public_ux_review_note(
            notes_path=notes_path,
            page="Unknown",
            viewport="desktop",
            first_answer_visible="yes",
            primary_next_action_visible="yes",
            advanced_details_collapsed="yes",
            classification="resolved",
            notes="No row.",
        )
    except ValueError as exc:
        assert "No public UX review note row matched Unknown / desktop" in str(exc)
    else:
        raise AssertionError("Expected unknown page to raise ValueError")


def test_record_public_ux_review_note_cli_honors_output_dir(tmp_path, monkeypatch, capsys):
    notes_path = write_public_ux_review_notes(tmp_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "public_ux_review_checklist",
            "--record-note",
            "--page",
            "Home",
            "--viewport",
            "desktop",
            "--first-answer-visible",
            "yes",
            "--primary-next-action-visible",
            "yes",
            "--advanced-details-collapsed",
            "yes",
            "--classification",
            "resolved",
            "--note-text",
            "CLI output-dir respected.",
            "--output-dir",
            str(tmp_path),
        ],
    )

    main()

    captured = capsys.readouterr()
    text = notes_path.read_text(encoding="utf-8")

    assert f"Updated: {notes_path}" in captured.out
    assert "| Home | desktop | yes | yes | yes | resolved | CLI output-dir respected. |" in text


def test_record_public_ux_review_note_cli_defaults_to_next_pending_row(tmp_path, monkeypatch, capsys):
    notes_path = write_public_ux_review_notes(tmp_path)

    monkeypatch.setattr(
        "sys.argv",
        [
            "public_ux_review_checklist",
            "--record-note",
            "--first-answer-visible",
            "yes",
            "--primary-next-action-visible",
            "yes",
            "--advanced-details-collapsed",
            "yes",
            "--classification",
            "resolved",
            "--note-text",
            "CLI used next pending row.",
            "--output-dir",
            str(tmp_path),
        ],
    )

    main()

    captured = capsys.readouterr()
    text = notes_path.read_text(encoding="utf-8")

    assert f"Updated: {notes_path}" in captured.out
    assert "| Home | desktop | yes | yes | yes | resolved | CLI used next pending row. |" in text
    assert "next_pending_review: Home | phone | http://localhost:8501/?mode=public" in captured.out
