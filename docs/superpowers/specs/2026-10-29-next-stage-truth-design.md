# Next-Stage Truth Design

## Intent

Make the local product's saved evidence and next safe action understandable after the code-only SEC evidence merge. Keep source rights, coverage, and readiness decisions separate from software availability.

## Scope and constraints

- `make next-stage`, standalone profile-context text/JSON, project-status JSON/CSV and human check, and dashboard cards name verified saved readiness separately from working-universe planning. A saved readiness numerator is never presented over the working-universe denominator. The fast status path marks working-universe coverage unavailable when it has only a saved readiness report.
- Discover, Company Workbench, and Monitor explain when the two local six-company inspections cannot be read. The state remains unavailable and makes no field-change claim.
- The active roadmap and completion log identify the code-only merge and its missing local receipts on a clean checkout.
- A local-only rights and identity decision packet records exact remaining review questions for the expanded inventory and inherited baseline. It grants no rights.
- No canonical data, readiness snapshot, source-rights registry, financial calculation, or recommendation state changes.

## Approach

Use the selected-profile readiness report for saved coverage and the onboarding ticker rows for working-universe planning. Publish both as `coverage_populations` in the status payload, identify the profile and data path, and name each legacy summary count's origin separately. The dashboard reads the current selected-profile readiness report even when a status artifact already has older saved counts; absent, malformed, or mismatched coverage is unavailable. Keep planning decisions and stage states intact while stage evidence and user-facing fractions use explicit populations. Changing the underlying readiness engine would cross its review gate. Keep the rights packet under ignored `outputs/local` so source-derived audit material cannot enter a public commit by accident.

## Acceptance

Regression tests distinguish divergent saved and working populations, equal-size but different cohorts, a missing or malformed saved report, a legacy status artifact, profile mismatch, and a saved report that changed after the status artifact. The missing six-company inspection pair explains its blocked state in all three surfaces. Read-only status, public wording, focused tests, and the existing automated release checks pass without tracked data or config changes.
