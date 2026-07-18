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


def test_pilot_review_template_has_task_based_scorecard_without_investment_opinions():
    body = Path("docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Optional Task-Based Pilot" in body
    assert "Find a company with a ready operating-company DCF" in body
    assert "Explain why an ETF or index proxy excludes company DCF" in body
    assert "Explain what the product must not be used for" in body
    for signal in (
        "Task success",
        "Moderator help required",
        "Readiness comprehension",
        "Misuse risk",
        "Trust in evidence",
        "Perceived performance",
        "Repeat-use case",
    ):
        assert signal in body
    assert "Do not ask whether the reviewer would buy or sell" in body


def test_pilot_review_feedback_make_target_is_read_only_and_discoverable():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "pilot-review-feedback:" in makefile
    assert "pilot-feedback-closeout:" in makefile
    target = makefile.split("pilot-review-feedback:", 1)[1].split("\n\n", 1)[0]
    closeout_target = makefile.split("pilot-feedback-closeout:", 1)[1].split("\n\n", 1)[0]

    assert "docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md" in target
    assert "docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv" in target
    assert "cp docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv /tmp/stock-command-center-pilot-feedback.csv" in target
    assert "10-20 external reviewers" in target
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in target
    assert "not data proof" in target.lower()
    assert "does not refresh data, import rows, stage files, commit, push, or deploy" in target
    assert "Commit a feedback log only after removing personal information" in target
    assert "docs/PILOT_FEEDBACK_CLOSEOUT_CHECKLIST.md" in closeout_target
    assert "reproducible_ui_issue" in closeout_target
    assert "environment_limited" in closeout_target
    assert "intentionally_deferred" in closeout_target
    assert "does not refresh data, import rows, stage files, commit, push, deploy, or publish feedback" in closeout_target


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
        "reviewer_signal",
        "closeout_outcome",
        "reproducible_issue_route",
        "reproducible_issue_viewport",
        "evidence_pointer",
        "task_success",
        "moderator_help_required",
        "readiness_comprehension",
        "misuse_risk",
        "trust_in_evidence",
        "perceived_performance",
        "repeat_use_case",
    ):
        assert column in header

    body = path.read_text(encoding="utf-8")
    for outcome in (
        "clear",
        "reproducible_ui_issue",
        "documentation_gap",
        "environment_limited",
        "intentionally_deferred",
    ):
        assert outcome in body
    assert "No names account details investment opinions price targets trade decisions or portfolio information" in body
    assert "buy" not in body.lower()
    assert "sell" not in body.lower()


def test_pilot_feedback_closeout_checklist_keeps_feedback_out_of_data_gates():
    body = Path("docs/PILOT_FEEDBACK_CLOSEOUT_CHECKLIST.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    runbook = Path("docs/PILOT_RUNBOOK.md").read_text(encoding="utf-8")

    for outcome in (
        "clear",
        "reproducible_ui_issue",
        "documentation_gap",
        "environment_limited",
        "intentionally_deferred",
    ):
        assert outcome in body
        assert outcome in runbook

    assert "not data proof" in body.lower()
    assert "Do not expand coverage, add providers, or apply imports from reviewer feedback alone." in body
    assert "make pilot-feedback-closeout" in readme
    assert "docs/PILOT_FEEDBACK_CLOSEOUT_CHECKLIST.md" in readme
    assert "make pilot-feedback-closeout" in runbook
    assert "make public-check" in body


def test_pilot_review_invitation_is_a_short_privacy_safe_entry_point():
    invitation = Path("docs/PILOT_REVIEW_INVITATION.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    linkedin_brief = Path("docs/LINKEDIN_PROJECT_BRIEF.md").read_text(encoding="utf-8")

    assert "Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History" in invitation
    assert "under three minutes" in invitation
    assert "Where did you start?" in invitation
    assert "What could you use now?" in invitation
    assert "What was blocked or excluded?" in invitation
    assert "What would you do next?" in invitation
    assert "Do not send names, account details, investment opinions, price targets, trade decisions, or portfolio information." in invitation
    assert "docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md" in invitation
    assert "docs/PILOT_FEEDBACK_CLOSEOUT_CHECKLIST.md" in invitation
    assert "not data proof" in invitation.lower()
    assert "docs/PILOT_REVIEW_INVITATION.md" in readme
    assert "docs/PILOT_REVIEW_INVITATION.md" in linkedin_brief


def test_commercial_beta_pilot_contract_is_task_based_and_truthful():
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    runbook = Path("docs/PILOT_RUNBOOK.md").read_text(encoding="utf-8")
    decision = Path("docs/PRODUCT_DIRECTION_DECISION.md").read_text(encoding="utf-8")

    assert "## Now: Commercial Research Beta Foundation" in roadmap
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in roadmap
    assert "local Commercial Research Beta foundation" in readme
    assert "not a hosted or commercially launched product" in readme
    assert "10 to 20" in runbook
    for metric in (
        "Task success",
        "Time to first answer",
        "Readiness comprehension",
        "Misuse risk",
        "Trust in evidence",
        "Perceived performance",
        "Repeat-use case",
    ):
        assert metric in runbook
    assert "awaiting_external_review" in decision
    assert "awaiting_reviewed_source" in decision
    assert "external_account_required" in decision


def test_commercial_beta_pilot_uses_the_research_workflow_and_nine_tasks():
    template = Path("docs/PILOT_REVIEW_FEEDBACK_TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Commercial Research Beta Tasks" in template
    assert "Research Desk -> Discover -> Company Workbench -> Monitor" in template
    for task in (
        "Identify the focused cohort and freshness state",
        "Use Discover to select one reviewable company",
        "Explain what can be used now",
        "Identify one withheld input",
        "Review Business Trend, Valuation, and Forward View boundaries",
        "Use Monitor to determine whether verified evidence changed",
        "State why the product is research-only",
    ):
        assert task in template
    assert "Do not fabricate reviewer sessions, completion rates, quotes, or findings" in template
