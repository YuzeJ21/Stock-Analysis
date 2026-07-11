# Coverage Continuity Runbook

Use this continuity contract when running a long next-stage roadmap session
without reopening stale blocker loops.

```text
Continue in the repository root.

Start from current repo truth, not chat memory.

Objective:
Continue the Stock Research Command Center next-stage roadmap until the pilot
package, source-boundary workflow, and coverage-proof surfaces are cleaner than
the current state. Do not stop just because a ticker, provider, source path, or
batch has no usable data. If a data path is exhausted, record or preserve the
truthful blocked state and pivot to the next executable product, proof, workflow,
documentation, QA, or packaging improvement.

Current stage to verify:
- Controlled external pilot is allowed only with manual gates.
- Price rows are complete for the tracked universe, but a small set of
  short-history depth items may remain partial because public providers only
  return post-listing history.
- Fundamentals/DCF, share count, peer mapping, earnings, and analyst-estimate
  lanes remain proof-gated.
- Current source-proof queues may already be reviewed/exhausted. Do not repeat
  stale loops unless new provider data, keyed sources, reviewed manual rows, new
  tickers, or changed blockers appear.
- The repo may be synced or ahead of GitHub; verify before pushing. It may also
  contain broad generated CSV/report churn. Keep generated churn excluded unless
  it is intentionally reviewed.

Product principle:
Data readiness first. Analysis second. Research decision last.

Guardrails:
- Research-only.
- No investment advice.
- No broker trading.
- No broker integration beyond explicitly configured read-only market data.
- No order routing.
- No auto-trading.
- No direct buy/sell instructions.
- Do not fabricate prices, fundamentals, shares, market cap, peers, earnings,
  estimates, valuation inputs, metrics, rankings, or recommendations.
- Preserve ready, partial, blocked, excluded, supported, auto_supported,
  human_reviewed_supported, candidate_context_only, still_blocked, and skipped.
- Do not stage generated CSV/JSON/report churn unless the exact artifact is
  intentionally reviewed evidence.
- Do not push unless explicitly asked.

Start:
- git status --short --branch --untracked-files=no
- git log -5 --oneline
- make diff-hygiene-summary
- make project-status
- make provider-setup-checklist
- make readiness-ops-center
- make coverage-frontier TOP_N=10
- make pilot-readiness-check TOP_N=10
- make public-wording-check
- git diff --check

Non-stop rule:
- Do not mark the overall goal blocked while any executable next step remains.
- A ticker-level or lane-level still_blocked, skipped, excluded, or
  candidate_context_only result is valid progress and must not stop the goal.
- Never retry the same unavailable provider/source path repeatedly in one
  session.
- If no data-changing source path is executable, switch to product workflow,
  public/pilot packaging, QA evidence, docs, guardrails, or tested helper
  extraction.
- Never invent data so a lane appears complete.

Source gate:
1. Read `make project-status` first.
2. If it says source-proof queues are exhausted, run and use
   `make provider-setup-checklist`; do not run broad trusted-data candidate
   loops.
3. If keyed providers are missing, keep them as setup-needed and continue with
   product/workflow improvements.
4. If a provider becomes available, run only that provider's smoke command,
   then validate and preview before any apply.
5. Apply rows only when validation passes, preview scope is narrow and intended,
   rejected rows are zero, source provenance exists, and no fabricated values are
   introduced.

Work priority:
1. Keep the pilot package clean:
   - make public-check
   - make public-release-package
   - make browser-qa-evidence
   - keep broad generated churn excluded
2. Improve the first-screen workflow:
   - public visitor path
   - Coverage Summary / What Can I Use
   - Data Health next action
   - Proof History
   - provider setup/source-boundary surface
3. Improve proof clarity:
   - decision proof queue
   - reviewed-batch proof ledger
   - optional-context boundary
   - peer candidate vs trusted peer wording
   - generated artifact hygiene
4. Run one narrow source-backed coverage slice only if the source gate says it
   is executable:
   - inspect packet
   - stage source-backed rows
   - validate
   - preview
   - apply only after the gate passes
   - rebuild readiness/report
   - record supported, still_blocked, skipped, excluded, or
     candidate_context_only
5. If no coverage slice is executable, continue with tested product/docs/QA
   improvements that reduce operator confusion and pilot risk.
6. For short price-history depth work, inspect one ticker at a time, record a
   reviewed `still_blocked` outcome when Stooq/Yahoo cannot verify enough real
   OHLCV history, and move to the next ticker without retrying the same source
   path.

Verification after every code/docs/product slice:
- python3 -m pytest tests -q
- make public-wording-check
- make pilot-readiness-check TOP_N=10
- make readiness-ops-center
- make coverage-frontier TOP_N=10
- make diff-hygiene-summary
- git diff --check
- make staged-hygiene-check if anything is staged

Commit rule:
- Stage only intentional product/code/docs/test files or reviewed proof/evidence
  artifacts.
- Keep broad generated CSV/JSON/report churn excluded.
- Commit locally when tests and hygiene pass.
- Do not push unless explicitly asked.

Final response every turn:
1. Current repo/GitHub status
2. Current pilot status
3. Coverage by lane
4. Source/provider availability
5. Product/proof slice worked
6. Rows staged/applied, if any
7. Tests/checks run
8. Commits created
9. Generated artifacts excluded
10. Exact next executable step
11. Whether safe to push/share
```

Plain-English contract:

- If coverage data is available, expand coverage through the source-backed gate.
- If coverage data is not available, improve the product so operators stop
  wasting time on blocked loops.
- Do not stop for provider gaps.
- Do not fabricate data.
- Do not push without explicit approval.
