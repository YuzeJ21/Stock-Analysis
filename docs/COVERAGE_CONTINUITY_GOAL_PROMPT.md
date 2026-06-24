# Coverage Continuity Contract

Use this copy-pasteable continuation contract when you want an automation run to keep expanding coverage without stalling on one unavailable source path.

```text
Continue Stock Research Command Center coverage proof work until every coverage lane is updated to one of: supported, still_blocked, skipped, or excluded.

Workspace: current repo root

Start from current repo truth, not chat memory.

Product principle:
Data readiness first. Analysis second. Research decision last.

Guardrails:
- Research-only.
- No investment advice.
- No broker integration.
- No auto-trading.
- No order routing.
- No direct buy/sell instructions.
- Do not fabricate prices, fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, metrics, or recommendations.
- Preserve ready, partial, blocked, excluded, supported, still_blocked, and skipped states.
- Do not stage generated CSV/JSON/report churn unless intentionally reviewed evidence.
- Do not push unless I explicitly ask.

Non-blocking rule:
- The overall goal must not stop because one source path fails.
- Do not mark the overall goal blocked while any executable lane, candidate, fallback research path, workflow improvement, or read-only verification path still exists in the current session.
- Ticker-level `still_blocked`, `skipped`, or `excluded` outcomes are valid slice outcomes and must not by themselves turn the whole goal into blocked status.
- Run one session preflight at the start:
  - git status --short --branch
  - make diff-hygiene
  - make status-check TOP_N=5
  - make readiness-ops-center
  - make coverage-frontier TOP_N=10
  - make session-source-preflight SEC_USER_AGENT='Name email@example.com'
- Treat the latest `make session-source-preflight` output as the session truth for lane selection.
- Commands that choose the next lane or candidate should reuse that session truth instead of retrying unavailable SEC/Yahoo-backed fundamentals paths in the same session.
- If SEC access fails, record session_sec_unavailable and do not retry SEC-backed fundamentals/share-count candidates again in that session.
- If yfinance fails, mark session_yfinance_unavailable and do not retry Yahoo-backed fundamentals again in that session.
- If both SEC and yfinance are unavailable, pivot immediately to another executable lane instead of blocking the goal.
- Never fabricate data to make coverage appear complete.

Lane selection rule:
1. Use SEC-backed fundamentals/share-count proof only if SEC is available in this session.
2. Otherwise use reviewed local fundamentals only when the session preflight says they can fix current share-count or fundamentals blockers.
3. Otherwise use `make yfinance-stage TICKERS=...` only when the optional research dependency is installed and the source path is working.
4. Otherwise use configured API fallback paths through `make fundamentals-source-ladder TICKERS=...` or `make fundamentals-source-ladder-queue TOP_N=...`; the fundamentals ladder tries FMP, Alpha Vantage, then Finnhub when `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, or `FINNHUB_API_KEY` is configured. For price blockers, use `make price-refresh-loop ... PROVIDER=auto`; the price ladder tries Yahoo, Stooq, then configured FMP, Alpha Vantage, and Finnhub fallbacks.
5. Otherwise switch to another executable lane:
   - peer candidate alignment
   - peer mapping proof
   - peer valuation input proof from local reviewed data
   - share count proof from reviewed local rows
   - earnings optional manual lane
   - analyst estimates optional manual lane
   - coverage summary / workflow / evidence capture improvements
6. Never retry the same unavailable source path repeatedly in one session.

Peer workflow rule:
- Split peer work into two levels:
  - candidate peer alignment
  - trusted peer mapping proof
- Use separate files for each layer:
  - candidate import draft: `data/imports/peer_candidates.csv`
  - candidate canonical layer: `data/peer_candidates.csv`
  - trusted import draft: `data/imports/peers.csv`
  - trusted canonical layer: `data/peers.csv`
- Candidate peer alignment is allowed to use:
  - current repo sector/industry context
  - SIC / NAICS / exchange / company-profile context
  - public company descriptions, filings, investor-relations pages, and other public research context
  - model-assisted synthesis from public information when stronger direct competitor evidence is not feasible in the current session
- Candidate peer alignment must stay explicitly labeled as one of:
  - candidate
  - fallback_context
  - research_only
- Candidate peer alignment can help:
  - choose the next peer lane
  - draft peer groups and rationales
  - rank likely peers
  - prepare source-review rows
- UI/report wording should reflect the split explicitly:
  - `candidate only` means the candidate layer exists in `data/peer_candidates.csv`
  - `trusted peer proof pending` means peer-relative valuation stays withheld
  - `trusted peer-ready` means reviewed `data/peers.csv` rows and follow-through inputs passed readiness
- Candidate peer alignment must not:
  - be written as trusted peer proof automatically
  - unlock peer-relative valuation automatically
  - be described as source-backed peer mapping unless reviewed evidence is recorded
- Trusted peer mapping proof still requires reviewed rows, validate/preview/apply, rebuilt readiness, and the normal proof loop before peer-relative valuation is treated as available.

Current first target:
1. Refresh ALOY first only if its fundamentals row still has the old epoch-shaped `as_of_date`; use:
   - make yfinance-stage TICKERS=ALOY
   - make imports-validate
   - make imports-preview
   - make imports-apply
   - make dcf-readiness
   - make readiness
   - make stock-report-md TICKER=ALOY
2. Then continue one narrow slice at a time in this order:
   - Peer Mapping Proof
   - Share Count Proof
   - Fundamentals / DCF Proof
   - Peer Valuation Inputs Proof
   - Earnings optional lane
   - Analyst Estimates optional lane
3. Choose the next candidate from:
   - make trusted-data-pilot-candidates TOP_N=10
   - make trusted-data-pilot-packet TICKER=<ticker>

Per-slice rule:
- inspect source path
- validate
- preview
- apply only if source-backed and intended
- rebuild readiness/report
- record outcome
- move on

Peer-slice fallback:
- If trusted peer proof is not feasible for the current ticker in this session, do not block the overall goal.
- Instead:
  - produce a candidate peer set with rationale from public context or model synthesis
  - label it candidate / fallback_context / research_only
  - record whether trusted peer proof remains still_blocked, skipped, or excluded
  - continue to the next executable candidate or lane
- Do not promote candidate peers into trusted peer mappings without the reviewed import/proof workflow.
- Do not reuse the same peer-blocked ticker repeatedly in the same session once its outcome has already been recorded with evidence.

Autonomous boundary:
- If SEC is blocked, yfinance is unavailable, and no reviewed local source rows exist, autonomous work cannot create new fundamentals/share-count coverage from scratch.
- If I do not want human intervention, continue only with executable lanes already backed by reviewed local rows or read-only monitoring.
- In that case, keep moving with:
  - read-only readiness/status/public checks
  - dry-run price planning or capped price coverage work
  - peer candidate alignment
  - peer follow-through when reviewed local peer rows already exist
  - optional-context lanes only when reviewed local rows already exist
  - workflow, coverage-summary, or evidence-capture improvements
- If no executable reviewed-source lane exists, record the candidate/lane as still_blocked, skipped, or excluded with evidence and move to the next executable item.

Per-slice process:
- inspect source path
- validate
- preview
- apply only if the gate passes
- rebuild readiness/report
- record outcome
- move on

Verification after each applied slice:
- python3 -m pytest tests -q
- make status-check TOP_N=5
- make readiness-ops-center
- make coverage-frontier TOP_N=10
- make public-wording-check
- make diff-hygiene
- git diff --check
- make staged-hygiene-check if anything is staged

Final response each turn:
1. Current coverage by lane
2. Session source availability
3. Candidate or lane worked
4. Source proof inspected
5. Rows staged/applied or not applied
6. Validation/preview/apply result
7. Rebuilt readiness/report result
8. Outcome state
9. Exact next executable lane
10. Whether safe to push/share
```

Plain-English rule:

- SEC unavailable should remove SEC-backed lanes from the current session, not stop the overall workflow.
- yfinance unavailable should remove Yahoo-backed fundamentals from the current session, not stop the overall workflow.
- Candidate peers are allowed as research context and planning help.
- Trusted peers still require the reviewed source-proof path.
- No-human-intervention mode means the automation run should keep advancing on truthful, executable paths.
- Truthful autonomous progress is allowed.
- Fabricated coverage is not.
