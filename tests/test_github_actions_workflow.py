import re
import shlex
from pathlib import Path

import yaml


WORKFLOW_PATH = Path(".github/workflows/commercial-research-beta.yml")


def test_commercial_research_beta_workflow_is_minimal_pr_only_gate():
    assert WORKFLOW_PATH.exists(), "commercial research beta PR workflow is missing"
    source = WORKFLOW_PATH.read_text(encoding="utf-8")
    # GitHub uses YAML 1.2: BaseLoader preserves `on` as a key rather than the
    # YAML 1.1 boolean used by PyYAML's default safe loader.
    workflow = yaml.load(source, Loader=yaml.BaseLoader)

    assert workflow["on"] == {"pull_request": {"branches": ["main"]}}
    assert workflow["permissions"] == {"contents": "read"}
    assert {"research-journey", "local-engineering-gate"} <= set(workflow["jobs"])
    assert "python3 -m pytest tests -q" not in source

    prohibited_fragments = (
        "secrets.",
        "upload-artifact",
        "deploy",
        "make readiness",
    )
    assert not [fragment for fragment in prohibited_fragments if fragment in source]
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            command = step.get("run", "")
            # Provider-named tests and pytest's no:cacheprovider option are
            # valid local checks; invoking a provider entry point is not.
            assert re.search(r"\bmake\s+\S*provider\S*", command) is None
            assert re.search(r"(?:^|\s)-m\s+src\.\S*provider\S*", command) is None


def test_research_journey_and_engineering_gates_run_independently_with_declared_extras():
    workflow = yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    pr_head = "${{ github.event.pull_request.head.sha }}"
    expected_commands = {
        "research-journey": ["make research-journey-check"],
        "local-engineering-gate": [
            "make test",
            "make dashboard-smoke",
            "make research-dashboard-render-smoke",
            "make public-wording-check",
            'make pr-range-hygiene-check BASE_SHA="$PR_BASE_SHA" HEAD_SHA="$PR_HEAD_SHA"',
            'git diff --check "$PR_BASE_SHA...$PR_HEAD_SHA"',
        ],
    }
    for name, required_commands in expected_commands.items():
        job = workflow["jobs"][name]
        assert job["runs-on"] == "ubuntu-latest"
        assert job["timeout-minutes"] == ("20" if name == "research-journey" else "90")
        assert not {"needs", "if", "continue-on-error"}.intersection(job)
        expected_env = {"PYTHONDONTWRITEBYTECODE": "1"}
        if name == "local-engineering-gate":
            expected_env.update(
                PR_BASE_SHA="${{ github.event.pull_request.base.sha }}",
                PR_HEAD_SHA=pr_head,
            )
        assert job["env"] == expected_env

        steps = job["steps"]
        assert not any({"if", "continue-on-error"}.intersection(step) for step in steps)
        actions = [step for step in steps if "uses" in step]
        assert [step["uses"] for step in actions] == [
            "actions/checkout@v6", "actions/setup-python@v6"
        ]
        assert actions[0]["with"] == {"fetch-depth": "0", "ref": pr_head}
        assert actions[1]["with"] == {"python-version": "3.12"}
        assert steps[:2] == actions

        commands = [step["run"] for step in steps if "run" in step]
        install = shlex.split(commands[0])
        assert install[:-1] == ["python3", "-m", "pip", "install", "-e"]
        assert install[-1].startswith(".[") and install[-1].endswith("]")
        assert set(install[-1][2:-1].split(",")) == {"dev", "workspace"}
        assert shlex.split(commands[1]) == [
            "python3", "-m", "playwright", "install", "--with-deps", "chromium"
        ]
        assert commands[2:] == required_commands
