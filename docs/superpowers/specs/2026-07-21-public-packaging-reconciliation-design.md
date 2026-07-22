# Public Packaging Reconciliation Design

## Status

Approved by the user through the July 21 public-package audit and the instruction to implement its recommendations.

## Goal

Make the public README, LinkedIn Featured guidance, share-check contract, performance evidence, and Featured thumbnail accurately represent the current answer-first Personal Research product without presenting generated readiness counts, draft-branch work, hosted availability, market validation, or research outputs as stronger evidence than they are.

## Scope

This is one bounded public-packaging slice. It changes:

- the README's first-review hierarchy;
- the LinkedIn project brief and copyable Featured guidance;
- the read-only LinkedIn share checklist;
- the Company Workbench first-useful performance marker;
- the curated LinkedIn Featured thumbnail and its browser-QA contract;
- roadmap and continuation documentation needed to preserve repository truth.

It does not change research calculations, readiness data, source rights, canonical data, report conclusions, routing behavior, hosting, licensing, or PR draft status.

## Design Decision

Use one external-reviewer entry point instead of competing `Personal Research Start Here` and `External Reviewer Start Here` sections.

The first screen of the README will:

1. name the project and the readiness-first principle;
2. show a reviewed Company Workbench image;
3. state that this is a local controlled portfolio beta, not a hosted or commercially launched product;
4. present Personal Research as the primary product workflow: Research Desk -> Discover -> Company Workbench -> Monitor;
5. retain the controlled Public five-page path as the secondary reviewer demo;
6. keep the research-only, source, hosting, reuse, and freshness boundaries visible;
7. route detailed operator commands and methodology to their dedicated documents.

The rest of the README may retain product depth, but the first-review section will not begin with provider setup, proof-queue mechanics, or long implementation inventories.

## LinkedIn Featured Contract

The recommended Featured item will describe the project as a local Python and Streamlit portfolio beta for evidence-first company research. It will name the four-step Personal Research workflow and state that usable, withheld, and advanced evidence remain separate.

The link target remains the stable GitHub repository only after the reviewed feature reaches the public default branch. While PR #113 is draft, the documentation must tell the owner to keep the existing stable item or label any PR/branch link as a draft engineering preview.

The copy must retain:

- research-only;
- no broker integration;
- no order routing or auto-trading;
- no investment advice;
- no hosted-product claim;
- no complete-coverage or current-data claim;
- no open-source or reuse claim under the controlled demo license.

## Visual Evidence

Replace `docs/assets/linkedin-public-dashboard.png` with a real `1200x627` Company Workbench capture from the current app.

The image must:

- show Company Workbench identity;
- show one selected-ticker answer with `Use now`, `Still withheld`, the Data Health handoff, and the stop condition;
- show the research-only boundary;
- avoid numerical universe, price-ready, DCF-ready, peer-ready, or source-date claims;
- avoid tracebacks, loading states, operator commands, raw tables, or generated artwork;
- preserve readable scale and intentional framing rather than stretching or approximating the product.

The browser-QA contract will identify the asset as a Workbench answer-first screenshot and treat it as product-flow evidence only.

## Performance Evidence

The Commercial Research performance gate will use `Use now` as the Company Workbench first-useful marker. `Company Workbench` remains a full-route marker, but the time-to-first-useful claim must be bound to the selected-company answer rather than the page title.

## Failure Handling

- If the current app cannot render the selected answer without numerical readiness claims in the target crop, do not replace the existing asset; record the visual blocker.
- If the image is not exactly `1200x627`, do not stage it.
- If README, LinkedIn, public wording, browser-QA, performance, or hygiene checks fail, do not commit or push the slice.
- If GitHub exact-head CI fails, keep PR #113 draft and report the failing gate.
- Generated CSV, JSON, report, sample-report, screenshot, timing, canonical-data, and readiness churn remains excluded unless it is the one explicitly reviewed thumbnail.

## Test Strategy

Add or update contracts that prove:

- the README starts with `External Reviewer Start Here` before any Personal Research subsection;
- the README names the four-step Personal Research workflow and keeps the five-step Public path secondary;
- the LinkedIn brief uses the new title and evidence-first description, contains the draft-link boundary, and rejects stale readiness-number claims in the Featured guidance;
- `make linkedin-share-check` prints the same current title, link boundary, image rule, and research-only stop rules;
- the Workbench performance first-useful marker is `Use now`;
- browser-QA identifies the LinkedIn asset as the Company Workbench answer-first visual with the required markers and dimensions.

Verification includes focused tests, the full test suite, dashboard and research render smoke, public wording, public check, LinkedIn share check, browser-QA evidence, public and Commercial Research performance gates, commercial beta release check, pilot readiness, PR-range hygiene, diff/staged hygiene, and whitespace checks.

## Acceptance Criteria

1. One external-reviewer entry point leads the README.
2. The primary product story is Research Desk -> Discover -> Company Workbench -> Monitor.
3. The Public five-page path remains available as a secondary controlled demo.
4. The LinkedIn Featured title and description match current product maturity and research boundaries.
5. The Featured image is a reviewed real Workbench capture at `1200x627` with no readiness counts.
6. The performance gate measures `Use now` instead of the Workbench page title.
7. All required local checks and exact-head CI pass.
8. Only intentional docs, tests, contracts, and the reviewed thumbnail are staged.
9. PR #113 remains open and draft; no merge or public deployment occurs.
