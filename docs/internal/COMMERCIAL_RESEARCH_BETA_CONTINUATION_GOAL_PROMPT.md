# Commercial Research Beta Continuation Goal Prompt

Use this prompt to continue the Stock Research Command Center in a new Codex task. It is intentionally repo-truth-first: commit hashes, counts, readiness states, and external dependencies must be reverified rather than copied forward as facts.

```text
/goal

Continue the Stock Research Command Center in:

/Users/yjian070/Documents/New project/.worktrees/personal-research-mode-mvp

Objective:

Advance the Stock Research Command Center from its current local Commercial Research Beta release-candidate stage through every applicable local, source, hosted-preview, beta-validation, evidence-depth, calibration, and operating-maturity gate. Continue one coherent verified slice at a time while any safe executable in-scope work remains. Do not redefine completion around the work that is already easy or local.

Persistence contract:

1. Start every continuation from live repository, roadmap, generated-artifact, test, runtime, remote-branch, and PR truth. Chat memory and the expected-state notes below are navigation aids only.
2. Continue automatically while any safe, meaningful, in-scope local task remains. Do not ask for approval for ordinary reversible local implementation, testing, documentation, or draft-PR updates already authorized by this goal.
3. Do not mark the goal blocked because one lane, provider, dataset, hosted account, reviewer, source, or calibration cohort is unavailable when another executable workstream exists.
4. When an external dependency is unavailable, classify it once, record the exact unblock condition and last evidence, avoid identical retry loops, and move immediately to the next executable local task.
5. Recheck an external dependency only when a credential, supplied dataset, account, URL, reviewer cohort, provider entitlement, source-rights decision, or other relevant external state has verifiably changed.
6. Do not repeat exhausted provider probes, broad-coverage refreshes, speculative peer sourcing, or identical source-limit loops.
7. Work one coherent independently tested slice at a time. Finish verification, exact staging, commit, push, roadmap/docs updates, and draft-PR updates before beginning the next slice.
8. Preserve explicit approval requirements for merging, public deployment, external account changes, credential use, destructive actions, purchases, public communication, or material scope expansion.
9. Never fabricate or infer data, forecasts, probabilities, evidence, events, peers, roles, comparability, outcomes, timestamps, sources, rights, reviewer results, hosted properties, recommendations, or completion evidence.
10. Do not mark the objective complete until the requirement-by-requirement completion audit directly proves every applicable exit gate. Passing local tests is not proof of source access, hosting, external beta validation, evidence depth, calibration, or operating maturity.
11. If every remaining task genuinely requires unavailable external input or new authority, leave completion unclaimed, produce the exact dependency ledger and resume checklist, and follow the active goal system's strict blocked audit. “Non-blocking” means pivoting to executable work, not retrying an unavailable dependency forever or pretending it is complete.
12. Keep the goal active whenever any applicable gate remains incomplete or unproven. A single unavailable dependency is not a reason to stop while another safe executable local slice remains; completion requires direct evidence for all applicable gates, not persistence theater or repeated external retries.

Expected lineage to verify, never assume:

- Branch: `codex/personal-research-mode-mvp`.
- Draft PR: https://github.com/YuzeJ21/Stock-Analysis/pull/113.
- Evidence-quality lineage anchor: commit `e0eea1f95` or a later verified descendant.
- No-write readiness-preview lineage anchor: commit `1f72a6d90` or a later verified descendant.
- The branch should be clean, pushed, and aligned with `origin/codex/personal-research-mode-mvp`.
- PR #113 must remain open and draft. Do not merge it.
- Generated CSV, JSON, readiness reports, stock reports, sample reports, screenshots, browser timing output, and other generated churn must remain excluded unless one exact artifact is intentionally reviewed and explicitly required.

Current locally implemented capabilities to verify:

- Personal Research Mode with Research Desk -> Discover -> Company Workbench -> Monitor.
- Answer-first hierarchy on all four Personal Research routes at desktop and phone widths.
- Mobile first-action density that keeps all five profile facts visible in two phone rows, removes only duplicated route-card freshness on phone, exposes route tasks sooner, and preserves the complete Company Workbench review path in a collapsed disclosure without changing readiness.
- SEC quarterly actual lineage with explicit Q4-table and EPS split-basis boundaries.
- Earnings Nowcast readiness and five-company cohort board.
- Prospective append-only point-in-time consensus collection contracts.
- Historical Valuation Regime, Research Outcome Review, and Catalyst Evidence Timeline.
- Forward View, Scenario Lab, Source Freshness Timeline, Research Comparison, Peer Read-Through Map, and Decision-Process Scorecard.
- Fail-closed provenance, source-rights, freshness, candidate-context, and synthetic-fixture controls.
- Shared pilot and reviewed-batch freshness that treats declared source dates newer than the saved readiness build as stale even when file mtimes look current; the read-only gate never runs `make readiness` or writes generated artifacts.
- No-write readiness impact preview via `make readiness-preview TOP_N=20`; it runs production readiness logic in memory, compares stable saved-versus-proposed states, writes nothing, and does not make saved readiness current.
- Same-mode Advanced Evidence continuity: Data Health and Proof History stay inside Personal Research mode, preserve the selected ticker, and expose Return to Company Workbench before evidence content. The navigation does not change readiness or evidence state.
- Peer evidence-quality contract separating relationship provenance, peer role, economic comparability, result context, trend readiness, and valuation-anchor eligibility.
- In-memory quarterly cash-generation evidence contract with independent operating-margin, free-cash-flow, and FCF-margin states, explicit filed-Q4 enforcement, Advanced-only source lineage, and no supplemental data file, writer, template, report, or generated artifact.
- Quarterly adapter acceptance harness for one in-memory company batch, with deterministic identity, commercial-rights, supported-field, cutoff, revision, component, compatibility, complete-period, and Q4 blockers; `accepted_for_review` always leaves production activation false and readiness promotions empty.

Truth boundaries that must remain unchanged unless direct evidence proves otherwise:

- Research-only; no investment advice, broker integration, order routing, auto-trading, direct buy/sell instructions, or post-earnings price prediction.
- Real-company Earnings Nowcast remains blocked until compatible quarterly actuals and exact-period point-in-time consensus independently pass.
- Numerical Beat/Miss probability remains withheld until at least 100 valid leakage-safe events pass Brier-score, calibration-bin, and benchmark-improvement gates.
- EPS split basis remains unverified without explicit primary proof.
- Q4 actuals require explicit SEC-filed Q4 result-table evidence; do not derive Q4.
- Synthetic fixtures are test-only.
- Empty valuation, catalyst, outcome, and consensus ledgers remain visibly empty.
- Candidate context cannot modify deterministic forecasts or become trusted evidence.
- A source-backed peer relationship is not automatically a valuation anchor. Only explicitly reviewed `core_peer` or `secondary_peer` rows with source/as-of provenance, relationship rationale, comparability basis, and `valuation_anchor_eligible=yes` may enter peer medians.
- Operating margin, free cash flow, and FCF margin remain withheld for real companies until a reviewed quarterly source adapter supplies compatible explicit observations. Their readiness cannot promote Revenue, EPS, DCF, consensus, peer, catalyst, outcome, backtest, or calibration states.
- Quarterly adapter acceptance is a local review-routing decision only. It cannot change source rights, load or write an adapter file, supply Company Workbench production observations, or promote readiness.
- Declared source dates newer than the saved readiness build must keep pilot, reviewed-batch, project-status, and profile-context freshness stale. File mtimes cannot override that evidence; only an intentional reviewed `make readiness` run can rebuild the generated snapshot.
- `make readiness-preview TOP_N=20` is inspection evidence only. It must not create or modify CSV, JSON, report, sample-report, screenshot, timing, directory, or bytecode artifacts; it cannot authorize a rebuild, promote readiness, or make stale counts current.

Current external dependency classifications to verify once, then avoid looping:

- Point-in-time consensus: `external_data_required`; the prospective ledger had 0 snapshots at the last verified check. Resume only when a permitted provider is configured or a reviewed CSV is supplied.
- Hosted preview: `external_account_required`; repository-side entrypoint, deterministic demo profile, runtime guidance, and checks exist, but no hosted URL or enforced access boundary has been proven.
- Controlled beta: `external_reviewers_required`; no 10-20 session reviewer cohort has been completed.
- Trusted-peer pilot: `external_source_and_review_required`; the local contract is implemented, but the existing legacy relationships have no inferred roles or anchor decisions. Resume with one bounded reviewed relationship, not a broad sourcing loop.
- Quarterly cash-generation source adapter: `external_source_and_review_required`; the no-file local contract is implemented, but no reviewed real-company adapter has supplied compatible operating-income, cash-from-operations, and capital-expenditure observations. Resume with one bounded company and explicit filed-Q4 evidence, not broad coverage.
- Quarterly adapter acceptance: the checked-in source-rights record must explicitly approve commercial use and list all three required component fields before a candidate can pass. The current SEC Companyfacts record does not list those fields; do not infer support or edit rights without reviewed evidence. Even `accepted_for_review` leaves real activation `external_source_and_review_required`.
- Numerical calibration: `external_evidence_required`; keep probability withheld until the valid-event threshold and quality gates pass.
- Operated platform controls: `external_account_and_operations_required`; authentication, workspace isolation, audit, retention, entitlements, monitoring, and health checks must be directly proven in the actual environment.

Execution order for each continuation:

1. Verify current branch, worktree, latest commits, upstream alignment, PR #113 draft status, ROADMAP.md, generated-artifact hygiene, current tests, and current product gates.
2. Review unresolved PR feedback and roadmap claims against live code and runtime behavior.
3. Audit the complete user workflow: Research Desk -> Discover -> Company Workbench -> Monitor.
4. Identify the highest-impact executable usability, methodology, evidence, reliability, or operating-readiness gap that moves an actual completion gate closer.
5. Implement one coherent slice with failing tests first where behavior changes.
6. Preserve independent readiness for actuals, consensus, Revenue, EPS, operating margin, free cash flow, FCF margin, valuation, trusted relationships, peer comparability, peer valuation anchors, catalysts, outcomes, backtesting, and calibration.
7. Keep technical evidence under Advanced unless it is required to explain the primary research answer.
8. Classify unavailable external dependencies once and move to the next executable local roadmap item.
9. Update tests, methodology, provenance, runbooks, ROADMAP.md, and this prompt when the verified stage or continuation contract changes.
10. Stage exact intentional paths only, commit the verified slice, push only the named branch, and update PR #113 while keeping it draft.
11. Continue to the next safe executable item rather than ending merely because one slice is complete.

Stage gates:

Stage 1 — Answer-first workflow hardening
- Exit only when all four Personal Research routes show the primary answer and one next action before technical evidence at desktop and phone widths.
- Current expected state: locally completed, including the verified mobile first-action density slice; reverify render, browser, wording, performance, and regression evidence.

Stage 2 — Permitted source activation
- Acquire one permitted append-only prospective point-in-time consensus snapshot for one reviewed ticker.
- Require exact fiscal period, independent Revenue/EPS comparability, durable source reference, publication and retrieval timestamps, provenance, freshness, revision handling, and suitable usage rights.
- Run validate, preview, rejection review, readiness, and provenance checks before any apply decision.
- Exit only when one repeatable source path demonstrates deterministic provenance, rights, freshness, failure handling, and append-only collection.

Stage 3 — Controlled hosted preview
- Use the deterministic demo profile; keep secrets and local research outside Git.
- Verify the actual URL, claimed access control, user isolation, health checks, rollback, and desktop/phone workflow.
- Exit only when the hosted runtime directly proves those properties without unsupported claims.

Stage 4 — Controlled beta validation
- Run 10-20 task-based reviewer sessions through the complete Personal Research workflow.
- Measure time to first answer, readiness comprehension, trust, misuse risk, perceived performance, and repeat-use intent.
- Record reproducible workflow defects only; reviewer feedback is not financial evidence.
- Exit only when reviewers complete the workflow without mistaking readiness, context, scenarios, or evidence gaps for advice or live-market certainty.

Stage 5 — Evidence-depth expansion
- Run a 25-50 company trusted-peer pilot only after trustworthy relationship sourcing and review capacity exist.
- Preserve peer role, rationale, comparability, source/as-of evidence, and explicit valuation-anchor decisions.
- Add optional earnings and estimates only from trusted, period-defined, source-backed rows.
- Expand valuation, catalyst, and outcome ledgers only from reviewed evidence.
- Continue chronological backtesting and calibration accumulation without relaxing the probability gate.
- Exit only when evidence depth expands through repeatable reviewed contracts without inferred broad coverage or readiness coupling.

Stage 6 — Operating maturity and product direction
- Add scheduled collection, rotation, alerts, and monitoring only after one provider path proves deterministic limits, provenance, rejection handling, and proof recording.
- Keep imports behind validate, preview, reviewed apply/skip, rebuilt readiness, and proof recording.
- Directly verify authentication, isolation, audit, retention, entitlements, monitoring, health checks, incident/rollback procedures, and owner capacity before claiming an operated platform.
- Choose explicitly among portfolio-quality prototype, maintained research tool, or operated platform only after hosted-preview, beta, source, peer, and operating evidence exists.

Verification after every meaningful implementation slice:

- focused tests for changed modules;
- `python3 -m pytest tests -q`;
- `make dashboard-smoke`;
- `make research-dashboard-render-smoke`;
- `make public-wording-check`;
- `make public-check`;
- `make pilot-readiness-check TOP_N=10`;
- `make diff-hygiene-summary`;
- `git diff --check`;
- relevant commercial performance or release gate when workflow/runtime behavior changes;
- `make staged-hygiene-check` and `git diff --cached --check` after exact staging.

Git and artifact rules:

- Never use `git add -A`.
- Stage exact reviewed product, code, documentation, test, and template paths only.
- Never stage broad generated CSV, JSON, readiness-report, stock-report, sample-report, screenshot, or timing churn.
- Commit only coherent verified slices.
- Push only to `codex/personal-research-mode-mvp`.
- Keep PR #113 draft and update it after each verified implementation slice.
- Do not merge into main or deploy publicly without explicit approval.

Completion audit before any completion claim:

- Derive every requirement from this goal, ROADMAP.md, PR #113, relevant specs/runbooks, and the current repository.
- Map each requirement and exit gate to authoritative evidence: code, tests, current artifacts, runtime behavior, source rows, provider rights, hosted URL behavior, reviewer records, calibration outputs, or operating controls.
- Classify every item as proven, contradicted, incomplete, indirect, or missing.
- Treat indirect, stale, synthetic-only, fixture-only, screenshot-only, local-only, or repo-contract-only evidence as insufficient for broader claims.
- Keep the goal active whenever any applicable gate remains incomplete or unproven.
- Declare completion only when every applicable stage exit gate has direct current evidence and no required work remains.

Required handoff after each slice:

1. Repository and PR status.
2. Current product stage and capabilities.
3. Roadmap item worked.
4. Changes made.
5. Tests, runtime checks, and product gates run.
6. Commit and push status.
7. Generated artifacts excluded.
8. External dependencies classified without repeat loops.
9. Remaining product gaps by stage.
10. Exact next executable step.
11. Whether the branch is safe for draft review.
12. Confirmation that the overall goal remains active unless every completion gate is directly proven.
```

The persistence language is deliberately evidence-bound. It prevents a single external dependency from stopping local progress, but it does not authorize fabricated completion, infinite retries, merging, deployment, credential use, destructive actions, or material scope expansion.
