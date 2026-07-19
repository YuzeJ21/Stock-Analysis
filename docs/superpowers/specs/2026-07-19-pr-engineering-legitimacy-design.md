# PR Engineering Legitimacy Design

## Purpose

PR #113 has extensive current local verification but no GitHub status checks and no independent review. Add one minimal pull-request-only GitHub Actions workflow so each proposed PR revision receives reproducible repository-side engineering evidence before human review.

This gate proves only that the checked-out revision passes the selected local tests and read-only product checks in GitHub's runner environment. It does not prove human review, source operation, data freshness, hosting, authentication, reviewer adoption, calibration, market demand, or product-market fit.

## Approaches Considered

### Selected: one explicit pull-request job

Create one workflow triggered only by pull requests targeting `main`. Use Python 3.12, install the checked-in requirements, and run the six commands named in the continuation contract as explicit steps.

This is the smallest legible gate, keeps failure attribution clear, and avoids giving CI broader authority than local verification requires.

### Rejected: call the full commercial release target

`make commercial-beta-release-check` intentionally repeats broad checks and prints extensive reviewer evidence. It is appropriate for local release audits, but unnecessarily expensive and noisy for every PR revision.

### Rejected: parallel jobs or a matrix

Separate jobs could reduce elapsed time, but they would repeat checkout and dependency installation and add orchestration that is not required for the first independent gate. The repository has no existing Actions convention that needs compatibility.

## Workflow Contract

- Trigger only on `pull_request` targeting `main`.
- Grant only `contents: read` permission.
- Run on GitHub-hosted Ubuntu with Python 3.12.
- Install the checked-in package in editable mode from `pyproject.toml` plus `pytest`, without adding a cache or generated artifact upload. This makes repository imports available to direct script entrypoints just as they are in the verified local environment.
- Set `PYTHONDONTWRITEBYTECODE=1` for the job.
- Run, in order:
  1. `python3 -m pytest tests -q`
  2. `make dashboard-smoke`
  3. `make research-dashboard-render-smoke`
  4. `make public-wording-check`
  5. `make diff-hygiene-summary`
  6. `git diff --check`
- Fail closed on any nonzero command.
- Do not run providers, refreshes, imports, readiness generation, deployment, schedules, secrets, hosted probes, or artifact uploads.

## Test Contract

A repository test reads the workflow as text and verifies the trigger, least-privilege permission, Python version, editable package and test-runner installation, required commands, and prohibited capabilities. The test fails while the workflow is absent or lacks the package install, then passes when the minimal file is present.

The test intentionally does not claim that a local YAML parse proves GitHub-hosted execution. The first successful Actions run on PR #113 remains the direct hosted CI evidence.

## Documentation And Product Boundary

Update `ROADMAP.md` and the commercial continuation contract to identify Stage 0 as implemented locally but externally pending until GitHub reports a completed check. Keep human review as a separate gate. Update PR #113 only after the local implementation checks pass and the branch is pushed.

No product research behavior, readiness state, source-rights decision, financial evidence, or generated artifact changes in this slice.

## Completion Criteria

- The contract test proves the workflow is minimal, PR-only, read-only, and contains every required command.
- Full local tests and all required non-writing product gates pass.
- Exact intentional files are staged; generated CSV, JSON, report, sample-report, screenshot, timing, readiness, and canonical-data churn remain excluded.
- The commit is pushed only to `codex/personal-research-mode-mvp`.
- PR #113 remains open and draft, and its body reports local verification separately from the pending or completed hosted Actions result.
