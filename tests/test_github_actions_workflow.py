from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/commercial-research-beta.yml")


def test_commercial_research_beta_workflow_is_minimal_pr_only_gate():
    assert WORKFLOW_PATH.exists(), "commercial research beta PR workflow is missing"

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "on:\n  pull_request:\n    branches: [main]" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "runs-on: ubuntu-latest" in workflow
    assert "python-version: \"3.12\"" in workflow
    assert "python3 -m pip install -r requirements.txt" in workflow
    assert "PYTHONDONTWRITEBYTECODE: \"1\"" in workflow

    required_commands = (
        "python3 -m pytest tests -q",
        "make dashboard-smoke",
        "make research-dashboard-render-smoke",
        "make public-wording-check",
        "make diff-hygiene-summary",
        "git diff --check",
    )
    positions = [workflow.index(command) for command in required_commands]
    assert positions == sorted(positions)

    prohibited_fragments = (
        "schedule:",
        "workflow_dispatch:",
        "push:",
        "secrets.",
        "upload-artifact",
        "deploy",
        "make readiness",
        "provider",
    )
    assert not [fragment for fragment in prohibited_fragments if fragment in workflow]
