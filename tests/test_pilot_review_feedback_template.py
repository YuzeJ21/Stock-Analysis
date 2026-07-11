from pathlib import Path


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


def test_pilot_review_feedback_make_target_is_read_only_and_discoverable():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "pilot-review-feedback:" in makefile
    target = makefile.split("pilot-review-feedback:", 1)[1].split("\n\n", 1)[0]

    assert "docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md" in target
    assert "5-10 external reviewers" in target
    assert "not data proof" in target.lower()
    assert "does not refresh data, import rows, stage files, commit, push, or deploy" in target
