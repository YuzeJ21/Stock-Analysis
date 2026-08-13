# Pull-Request Range Engineering Gate Design

## Problem

The hosted workflow checks a clean checkout with working-tree commands. Both
generated-artifact hygiene and whitespace can therefore inspect zero paths even
when the pull request changes hundreds of files.

## Contract

- The pull-request event supplies explicit base and head commit SHAs.
- Checkout fetches sufficient history and checks out the exact PR head.
- A read-only range-hygiene command resolves both values as commits and reads
  `git diff --name-status BASE...HEAD`.
- The command classifies every changed path through the existing hygiene rules,
  reports product, sample-report, generated CSV/JSON, and manual-review counts,
  and fails when generated CSV/JSON churn exists in the PR range.
- Manual-review paths remain explicitly reported; this generated-artifact gate
  does not silently recast them as product paths.
- Whitespace uses `git diff --check BASE...HEAD` against the same explicit
  event range.
- Tests create a temporary two-commit repository to prove a generated file that
  is absent from the working-tree diff is still found in the commit range.

## Workflow Boundaries

The workflow stays pull-request-only with `contents: read`. It has no secrets,
provider access, schedule, readiness generation, deployment, artifact upload,
or write permission. Range inspection is evidence about the PR diff only; it is
not human review or merge approval.
