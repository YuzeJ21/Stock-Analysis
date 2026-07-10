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
