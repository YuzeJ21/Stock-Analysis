from pathlib import Path


def test_scheduler_activation_checklist_blocks_mutating_jobs_until_gates_pass():
    body = Path("docs/SCHEDULER_ACTIVATION_CHECKLIST.md").read_text(encoding="utf-8")

    for phrase in (
        "default scheduler posture is read-only monitoring",
        "Provider setup alone is never activation proof.",
        "Do not schedule unattended imports, applies, commits, pushes",
        "make auto-refresh-status SCHEDULE=daily",
        "make auto-refresh-runbook SCHEDULE=daily",
        "validation, preview",
        "Rejected rows are zero",
        "Provenance exists",
        "No fabrication",
        "Proof is recorded",
    ):
        assert phrase in body

    assert "broker access" in body
    assert "recommendation workflows" in body


def test_scheduler_activation_make_target_is_read_only_and_discoverable():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "scheduler-activation-checklist:" in makefile
    target = makefile.split("scheduler-activation-checklist:", 1)[1].split("\n\n", 1)[0]

    assert "docs/SCHEDULER_ACTIVATION_CHECKLIST.md" in target
    assert "status-only monitoring" in target
    assert "does not refresh, import, apply, stage, commit, push, deploy, or expose secrets" in target
    assert "Never schedule unattended imports-apply, commits, pushes" in target
    assert "provider smoke, source proof, validation, preview, zero rejected rows, provenance, and proof recording" in target


def test_scheduler_activation_docs_are_linked_from_reviewer_and_operator_paths():
    readme = Path("README.md").read_text(encoding="utf-8")
    operator_guide = Path("docs/OPERATOR_GUIDE.md").read_text(encoding="utf-8")

    assert "make scheduler-activation-checklist" in readme
    assert "Scheduler maturity starts as status-only monitoring" in readme
    assert "make scheduler-activation-checklist" in operator_guide
    assert "Provider setup alone is never scheduling proof." in operator_guide
