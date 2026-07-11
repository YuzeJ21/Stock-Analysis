from pathlib import Path
import csv


def test_pilot_review_feedback_template_keeps_clarity_feedback_separate_from_data_proof():
    body = Path("docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md").read_text(encoding="utf-8")

    for heading in (
        "## Reviewer Task",
        "## Capture Sheet",
        "## Reproducible Issue Format",
        "## Evidence Boundary",
    ):
        assert heading in body
    for prompt in (
        "Where did you start?",
        "What could you use now?",
        "What was blocked or excluded?",
        "What would you do next?",
    ):
        assert prompt in body
    assert "not data proof" in body.lower()
    assert "Do not record names, account details, or investment opinions" in body
    assert "docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv" in body
    assert "cp docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv /tmp/stock-command-center-pilot-feedback.csv" in body
    assert "outside the repository" in body


def test_pilot_review_feedback_make_target_is_read_only_and_discoverable():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "pilot-review-feedback:" in makefile
    target = makefile.split("pilot-review-feedback:", 1)[1].split("\n\n", 1)[0]

    assert "docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md" in target
    assert "docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv" in target
    assert "cp docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv /tmp/stock-command-center-pilot-feedback.csv" in target
    assert "5-10 external reviewers" in target
    assert "not data proof" in target.lower()
    assert "does not refresh data, import rows, stage files, commit, push, or deploy" in target
    assert "Commit a feedback log only after removing personal information" in target


def test_pilot_review_feedback_log_template_is_anonymous_and_comparable():
    path = Path("docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv")
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))

    assert rows
    header = rows[0].keys()
    for column in (
        "review_label",
        "review_path",
        "ticker_or_example",
        "where_started",
        "usable_now",
        "blocked_or_excluded",
        "next_expected_action",
        "time_to_first_answer_minutes",
        "confusion_point",
        "outcome",
        "reproducible_issue_route",
        "reproducible_issue_viewport",
        "evidence_pointer",
    ):
        assert column in header

    body = path.read_text(encoding="utf-8")
    assert "No names account details investment opinions price targets trade decisions or portfolio information" in body
    assert "buy" not in body.lower()
    assert "sell" not in body.lower()
