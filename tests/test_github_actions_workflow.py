from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/commercial-research-beta.yml")


def test_commercial_research_beta_workflow_is_minimal_pr_only_gate():
    assert WORKFLOW_PATH.exists(), "commercial research beta PR workflow is missing"

    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "on:\n  pull_request:\n    branches: [main]" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "runs-on: ubuntu-latest" in workflow
    assert "python-version: \"3.12\"" in workflow
    assert "python3 -m pip install -e '.[dev]'" in workflow
    assert "python3 -m pip install -e . pytest" not in workflow
    assert "python3 -m playwright install --with-deps chromium" in workflow
    assert "PYTHONDONTWRITEBYTECODE: \"1\"" in workflow
    assert "uses: actions/checkout@v6" in workflow
    assert "uses: actions/setup-python@v6" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "actions/setup-python@v5" not in workflow
    assert "fetch-depth: 0" in workflow
    assert "ref: ${{ github.event.pull_request.head.sha }}" in workflow
    assert "PR_BASE_SHA: ${{ github.event.pull_request.base.sha }}" in workflow
    assert "PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}" in workflow

    required_commands = (
        "python3 -m playwright install --with-deps chromium",
        "make test",
        "make dashboard-smoke",
        "make research-dashboard-render-smoke",
        "make public-wording-check",
        'make pr-range-hygiene-check BASE_SHA="$PR_BASE_SHA" HEAD_SHA="$PR_HEAD_SHA"',
        'git diff --check "$PR_BASE_SHA...$PR_HEAD_SHA"',
    )
    positions = [workflow.index(command) for command in required_commands]
    assert positions == sorted(positions)
    assert "python3 -m pytest tests -q" not in workflow

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
