# Controlled Pilot Review Feedback

Use this template with 5-10 external reviewers after they open the GitHub demo package or the local `demo` profile. It measures product clarity and workflow reliability only. It does not collect market data, validate a source, change readiness, or support an investment conclusion.

## Reviewer Task

Ask the reviewer to follow the public path without operator instructions:

```text
Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History
```

Ask them to use one example ticker and answer these four questions in their own words:

1. Where did you start?
2. What could you use now?
3. What was blocked or excluded?
4. What would you do next?

Do not coach the answers. The purpose is to see whether the public workflow is self-explanatory in under three minutes.

## Capture Sheet

Record one row per review session outside the repository unless the note contains no personal information.

| Field | Record |
| --- | --- |
| Review label | Anonymous session label such as `R01`; do not use a full name. |
| Review path | GitHub-only or local demo profile. |
| Ticker/example | The example ticker or route the reviewer chose. |
| Where did you start? | Their first page or artifact opened. |
| What could you use now? | Their description of supported analysis or context. |
| What was blocked or excluded? | Their description of withheld or non-applicable analysis. |
| What would you do next? | Their next expected page or action. |
| Time to first answer | Approximate minutes to explain the product state. |
| Confusion point | Exact page, label, or route that caused confusion, if any. |
| Outcome | `clear`, `unclear`, or `environment_limited`. |

Do not record names, account details, or investment opinions. Do not ask reviewers for a stock recommendation, price target, trade decision, or personal portfolio information.

## Reproducible Issue Format

Turn only reproducible product issues into backlog items:

```text
Route: <public route or document>
Viewport: <desktop or phone>
Observed: <what the reviewer saw>
Expected: <the page question, one answer, or primary next action that was unclear>
Impact: <why this prevented the reviewer from understanding readiness or the next step>
Evidence: <screenshot or exact wording, with no personal information>
```

Prioritize first-viewport, route-order, wording, raw-detail visibility, mobile layout, and accessibility defects. Do not weaken readiness gates merely because a reviewer prefers a faster answer.

## Evidence Boundary

Pilot feedback is not data proof, source proof, or data freshness proof. It cannot unlock prices, fundamentals, shares, peers, earnings, estimates, valuation inputs, metrics, or recommendations.

Keep outcomes distinct:

- `clear`: the workflow was understandable; it does not prove analysis correctness.
- `unclear`: create a reproducible UX issue only when the route and observation are recorded.
- `environment_limited`: the local demo or browser could not be reviewed; do not treat it as a product defect without reproduction evidence.

After a UI change, rerun `make public-ux-review-notes-check`, `make dashboard-smoke`, `make browser-qa-evidence`, and `make public-check` before updating public screenshots or LinkedIn/GitHub wording.
