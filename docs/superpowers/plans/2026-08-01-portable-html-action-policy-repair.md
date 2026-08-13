# Portable HTML Action Policy Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Company Workbench portable HTML brief deterministically withhold active and modal-passive transaction-equivalent language without suppressing ordinary research, accounting, classification, record, or methodology prose.

**Architecture:** Extract the current token/state action policy from the HTML snapshot/renderer into one pure module, preserve `safe_html_brief_text(value)` as the compatibility and escaping boundary, and add a reverse passive scan from semantic endpoint head through a modal/auxiliary chain to a compatible action participle. Prove the policy first in isolation, then through every portable field family and every emitted HTML surface.

**Tech Stack:** Python 3.10+, standard-library `dataclasses`, `re`, and `unicodedata`; frozen HTML snapshot contracts; pytest 8+; existing Streamlit and browser/accessibility gates.

## Global Constraints

- Start from `docs/superpowers/specs/2026-08-01-portable-html-action-policy-repair-design.md` and current repository truth.
- Preserve `safe_html_brief_text(value)` and the exact fixed output `Withheld: reviewer-authored action language is not portable research evidence.`
- The policy is deterministic, local, offline, and fail-closed. No LLM, NLP service, API, network call, data provider, or probabilistic classifier.
- Do not add recommendations, rankings, transaction directions, position sizing, allocation, brokerage, order routing, auto-trading, current-market claims, expected-return scores, or probabilities.
- Preserve independent actuals, consensus, Revenue, EPS, valuation, peers, historical valuation, catalysts, outcomes, backtesting, and calibration states.
- Candidate context cannot modify deterministic scenarios or become trusted evidence. Synthetic fixtures remain test-only. Q4 actuals require explicit filed-Q4 evidence. EPS split basis remains unverified without explicit proof.
- Do not run readiness rebuilds, broad refresh/import/apply commands, or generated CSV/JSON/report/sample-report/screenshot/timing writers.
- Preserve the exact 18 pre-existing dirty generated CSV/report paths byte-for-byte and keep them unstaged. Never use `git add -A`.
- Technical evidence remains under Advanced unless required for the primary research answer.
- If the deterministic policy cannot pass both the adversarial and safe-control corpora, do not restore the forward-only scanner or ship a partial policy; keep the HTML preview/download unavailable behind the fixed withheld state and route the controlled-template fallback for separate review.
- Keep PR #113 open and draft. Push only `codex/personal-research-mode-mvp`. Do not merge or deploy publicly.

## File Map

- Create `src/portable_research_action_policy.py`: normalization, tokenization, safe exceptions, active scan, passive scan, and one pure public predicate.
- Create `tests/test_portable_research_action_policy.py`: isolated active/passive/safe-control/adversarial policy contract.
- Modify `src/company_workbench_html.py`: import the pure predicate; retain secrets, paths, URLs, HTML escaping, fixed withheld copy, snapshot construction, and renderer defense-in-depth.
- Modify `tests/test_company_workbench_html.py`: portable-field injection matrix and snapshot/fragment/document/byte assertions.
- Modify `scripts/public_wording_check.py`, `tests/test_public_wording_check.py`, and `tests/test_diff_hygiene.py`: include the new public product module in release policy.
- Modify `README.md`, `PRODUCT_SPEC.md`, `ROADMAP.md`, `docs/METHODOLOGY.md`, `docs/DASHBOARD_QA.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, and `tests/test_public_v1_release_docs.py`: correct stale completion, synchronization, and next-lane claims.
- Modify `docs/superpowers/specs/2026-08-01-portable-html-action-policy-repair-design.md`: record the user's written approval.

## Preflight And Protected-Artifact Baseline

Before Task 1, verify the existing linked worktree, branch, PR, remote ancestry, empty index, and exact dirty-path set. Capture hashes in this plan's ignored SDD workspace and compare them before every task commit and after the final matrix.

```bash
test "$(git branch --show-current)" = "codex/personal-research-mode-mvp"
test "$(git rev-parse --show-superproject-working-tree)" = ""
test "$(git rev-list --left-only --count origin/codex/personal-research-mode-mvp...HEAD)" = "0"
test "$(gh pr view 113 --json state --jq .state)" = "OPEN"
test "$(gh pr view 113 --json isDraft --jq .isDraft)" = "true"
test -z "$(git diff --cached --name-only)"
python3 - <<'PY'
import subprocess

expected = {
    "data/analyst_estimates_readiness.csv",
    "data/dcf_readiness.csv",
    "data/earnings_readiness.csv",
    "data/price_coverage_report.csv",
    "data/reports/analyst_estimates_readiness_report.csv",
    "data/reports/data_source_status.csv",
    "data/reports/dcf_readiness_report.csv",
    "data/reports/earnings_readiness_report.csv",
    "data/reports/feature_readiness_summary.csv",
    "data/reports/fundamentals_coverage_report.csv",
    "data/reports/peer_readiness_report.csv",
    "data/reports/peer_unlock_worklist.csv",
    "data/reports/price_coverage_report.csv",
    "data/reports/ticker_readiness_report.csv",
    "data/reports/universe_coverage_report.csv",
    "data/universe_master.csv",
    "outputs/feature_readiness_summary.csv",
    "outputs/peer_unlock_worklist.csv",
}
rows = subprocess.check_output(
    ["git", "status", "--porcelain=v1", "--untracked-files=all"],
    text=True,
).splitlines()
actual = {row[3:] for row in rows}
if actual != expected:
    raise SystemExit(f"unexpected worktree paths: {sorted(actual ^ expected)}")
PY
```

Hash command:

```bash
shasum -a 256 \
  data/analyst_estimates_readiness.csv \
  data/dcf_readiness.csv \
  data/earnings_readiness.csv \
  data/price_coverage_report.csv \
  data/reports/analyst_estimates_readiness_report.csv \
  data/reports/data_source_status.csv \
  data/reports/dcf_readiness_report.csv \
  data/reports/earnings_readiness_report.csv \
  data/reports/feature_readiness_summary.csv \
  data/reports/fundamentals_coverage_report.csv \
  data/reports/peer_readiness_report.csv \
  data/reports/peer_unlock_worklist.csv \
  data/reports/price_coverage_report.csv \
  data/reports/ticker_readiness_report.csv \
  data/reports/universe_coverage_report.csv \
  data/universe_master.csv \
  outputs/feature_readiness_summary.csv \
  outputs/peer_unlock_worklist.csv
```

---

### Task 1: Extract The Existing Active Policy Behind A Pure Interface

**Files:**
- Create: `src/portable_research_action_policy.py`
- Create: `tests/test_portable_research_action_policy.py`
- Modify: `src/company_workbench_html.py:33-194,212-215,361-608,611-626`
- Test: `tests/test_company_workbench_html.py`

**Interfaces:**
- Produces: `contains_portable_action_language(value: str) -> bool`.
- Preserves: `safe_html_brief_text(value: object) -> str` and its exact fixed withheld output.

- [ ] **Step 1: Write isolated characterization tests before creating the module**

Create `tests/test_portable_research_action_policy.py` with literal active-action and safe-control expectations:

```python
import builtins

import pytest

from src.portable_research_action_policy import contains_portable_action_language


@pytest.mark.parametrize(
    "text",
    (
        "buy common shares",
        "execute one large block trade",
        "open another position",
        "cover the short",
        "go strategically net long",
        "The note says the strategy executes trades.",
    ),
)
def test_existing_active_action_families_remain_non_portable(text):
    assert contains_portable_action_language(text) is True


@pytest.mark.parametrize(
    "text",
    (
        "The filing covers the current position disclosure.",
        "The model builds a current position estimate.",
        "Hold the current equity method constant.",
        "Held-to-maturity securities remain unchanged.",
        "Available-for-sale securities remain unchanged.",
        "No recommendation; not investment advice.",
    ),
)
def test_existing_reference_and_boundary_prose_remains_portable(text):
    assert contains_portable_action_language(text) is False


def test_policy_is_repeatable_and_never_opens_files(monkeypatch):
    def fail_open(*args, **kwargs):
        raise AssertionError("portable policy must not read files")

    monkeypatch.setattr(builtins, "open", fail_open)
    assert contains_portable_action_language("buy shares") is True
    assert contains_portable_action_language("buy shares") is True
```

- [ ] **Step 2: Run the new test to verify RED**

```bash
python3 -m pytest tests/test_portable_research_action_policy.py -q
```

Expected: collection fails because `src.portable_research_action_policy` does not exist.

- [ ] **Step 3: Move the existing policy without changing its behavior**

Move these units from `src/company_workbench_html.py` into the new pure module:

- action-family, boundary, classification, reference, accounting, and coordination constants currently at lines 33-194;
- `_ActionToken`;
- `_is_numeric_connector`, `_is_action_clause_boundary`, `_is_action_ignorable`, `_action_token_clauses`, `_token_texts`, both exact-removal helpers, phrase/reference/coverage helpers, `_family_has_action_endpoint`, and `_contains_semantic_action`;
- expose the old `_contains_action_language` behavior as:

```python
def contains_portable_action_language(value: str) -> bool:
    for clause in _action_token_clauses(value):
        action_tokens = _without_non_action_classifications(clause)
        action_tokens = _without_approved_negated_boundaries(action_tokens)
        if _contains_semantic_action(action_tokens):
            return True
    return False
```

Keep `_SECRET_PATTERN`, `_PATH_PATTERN`, `_SENSITIVE_PATH_SEGMENTS`, `_WITHHELD_ACTION`, `safe_html_brief_text`, safe-reference URL rules, and HTML escaping in `company_workbench_html.py`. Replace only the internal action call:

```python
from src.portable_research_action_policy import contains_portable_action_language

# inside safe_html_brief_text
if contains_portable_action_language(text):
    return _WITHHELD_ACTION
```

- [ ] **Step 4: Verify GREEN and unchanged HTML behavior**

```bash
python3 -m pytest tests/test_portable_research_action_policy.py -q
python3 -m pytest tests/test_company_workbench_html.py -q
```

Expected: the pure characterization tests pass and the complete existing HTML suite remains green.

- [ ] **Step 5: Refactor only after green**

Remove unused policy imports/constants from `company_workbench_html.py`. Keep `re` and `unicodedata` because secret/path/control-character and ticker checks still use them. Run the two commands from Step 4 again.

- [ ] **Step 6: Verify protected artifacts, stage exact files, and commit**

```bash
git diff --check
make diff-hygiene-summary
git add -- src/portable_research_action_policy.py src/company_workbench_html.py tests/test_portable_research_action_policy.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Extract portable research action policy"
```

---

### Task 2: Add Modal-Passive Detection And Whole-Artifact Proof

**Files:**
- Modify: `src/portable_research_action_policy.py`
- Modify: `tests/test_portable_research_action_policy.py`
- Modify: `tests/test_company_workbench_html.py:400-1010`

**Interfaces:**
- Consumes: `contains_portable_action_language(value: str) -> bool` from Task 1.
- Preserves: all HTML snapshot and renderer APIs.

- [ ] **Step 1: Add the six exact failing policy cases**

Add this literal RED corpus:

```python
@pytest.mark.parametrize(
    "text",
    (
        "Shares should be bought now.",
        "The stock should be sold.",
        "A trade should be executed.",
        "The order should be submitted.",
        "The position should be increased.",
        "Long exposure should be opened.",
    ),
)
def test_modal_passive_transaction_language_is_not_portable(text):
    assert contains_portable_action_language(text) is True
```

Add table-driven cases covering `must`, `should`, `can`, `could`, `may`, `might`, `will`, `would`, and `shall` with `be` and `get`; `is/are/was/were/been/being`; optional `not` or `never`; punctuation, Unicode hyphens, NFKC-width variants, and ignorable format characters. Keep expected values as literal booleans.

Add these exact safe controls:

```python
@pytest.mark.parametrize(
    "text",
    (
        "The position estimate should be increased.",
        "The trade record should be ordered by date.",
        "The equity method should be held constant.",
        "Securities are held to maturity.",
        "Assets are available for sale.",
    ),
)
def test_modal_reference_and_classification_prose_remains_portable(text):
    assert contains_portable_action_language(text) is False
```

- [ ] **Step 2: Add failing integration cases before production changes**

Extract the existing field-construction branches into the test-only helper:

```python
def _snapshot_with_portable_field_text(field_name: str, text: str):
    # Use the existing 24-field fixture mutations verbatim, then call
    # build_company_workbench_html_snapshot(_inputs(report, **changes)).
```

Parameterize at least one modal-passive example through every existing portable field case: overview metadata, selected answers, task title/body/badge, recency, quarterly/Revenue/EPS, peers/thesis/risk/catalyst/regime, Decision Lab, scenario method, evidence source/model/input identities, reference label, and nowcast verdict when its lane is otherwise eligible.

For every injected value, assert:

```python
snapshot = _snapshot_with_portable_field_text(field_name, unsafe)
fragment = html_brief.render_company_workbench_html_fragment(snapshot)
document = html_brief.render_company_workbench_html_document(snapshot)
download = html_brief.company_workbench_html_bytes(snapshot)

assert unsafe not in repr(snapshot)
assert unsafe not in fragment
assert unsafe not in document
assert unsafe.encode("utf-8") not in download
assert "Withheld: reviewer-authored action language is not portable research evidence." in repr(snapshot)
```

Also assert the affected field/lane state is unchanged or more restrictive; sanitation must never unlock a lane.

- [ ] **Step 3: Run the policy and integration selections to verify RED**

```bash
python3 -m pytest tests/test_portable_research_action_policy.py -q
python3 -m pytest tests/test_company_workbench_html.py -q -k 'modal_passive or passive_portable_field'
```

Expected: the six exact passive cases and their integration injections fail because the Task 1 policy is forward-only. Safe controls pass.

- [ ] **Step 4: Implement the bounded reverse semantic scan**

Add exact modal/auxiliary sets and reverse family definitions:

```python
_PASSIVE_MODALS = frozenset(
    {"must", "should", "can", "could", "may", "might", "will", "would", "shall"}
)
_PASSIVE_AUXILIARIES = frozenset(
    {"be", "been", "being", "is", "are", "was", "were", "get", "gets", "got", "getting"}
)
_PASSIVE_NEGATIONS = frozenset({"not", "never"})
_PASSIVE_MAX_CHAIN_TOKENS = 5
_PASSIVE_ACTION_FAMILIES = (
    (_SECURITY_ACTION_ENDPOINTS, _SECURITY_ACTION_STARTS),
    (_EXECUTION_ACTION_ENDPOINTS, _EXECUTION_ACTION_STARTS),
    (_POSITION_ACTION_ENDPOINTS | frozenset({"exposure", "exposures"}), _POSITION_ACTION_STARTS | _DIRECTIONAL_ACTION_STARTS),
    (_COVERING_ACTION_ENDPOINTS, _COVERING_ACTION_STARTS),
    (_DIRECTIONAL_ACTION_ENDPOINTS | frozenset({"exposure", "exposures"}), _DIRECTIONAL_ACTION_STARTS | _POSITION_ACTION_STARTS),
)
```

Implement `_contains_modal_passive_action(tokens)` with these rules:

1. The semantic endpoint is the token immediately before the modal or auxiliary chain. This makes `position estimate should be increased`, `trade record should be ordered`, and `equity method should be held` safe because the immediate head is not an endpoint.
2. A modal must reach `be` or `get` (including the auxiliary inflections above) before a compatible participle. A direct auxiliary may reach the participle without a modal.
3. Allow only the bounded modal, auxiliary, negation, and ordinary adverb positions already represented by tokens; stop after `_PASSIVE_MAX_CHAIN_TOKENS` or the clause boundary produced by the tokenizer.
4. Match the final action token only against the compatible family for the endpoint.
5. `exposure` is accepted only for position/directional families.
6. Run the existing exact classification and research-only boundary removal before both active and passive scans.
7. Negated constructions still return `True`; only the four exact approved research-only boundaries are removed.

Call the new scan from the pure public function:

```python
if _contains_semantic_action(action_tokens) or _contains_modal_passive_action(action_tokens):
    return True
```

- [ ] **Step 5: Verify GREEN, then refactor duplication**

```bash
python3 -m pytest tests/test_portable_research_action_policy.py -q
python3 -m pytest tests/test_company_workbench_html.py -q
```

After green, consolidate only shared family matching or token-window helpers. Re-run both commands and confirm all safe controls remain visible.

- [ ] **Step 6: Verify protected artifacts, stage exact files, and commit**

```bash
git diff --check
make diff-hygiene-summary
git add -- src/portable_research_action_policy.py tests/test_portable_research_action_policy.py tests/test_company_workbench_html.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Withhold modal passive HTML action language"
```

---

### Task 3: Wire Release Policy And Reconcile Documentation Truth

**Files:**
- Modify: `scripts/public_wording_check.py`
- Modify: `tests/test_public_wording_check.py`
- Modify: `tests/test_diff_hygiene.py`
- Modify: `README.md`
- Modify: `PRODUCT_SPEC.md`
- Modify: `ROADMAP.md`
- Modify: `docs/METHODOLOGY.md`
- Modify: `docs/DASHBOARD_QA.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `docs/superpowers/specs/2026-08-01-portable-html-action-policy-repair-design.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: the new policy module and focused GREEN evidence from Tasks 1-2.
- Produces: one consistent pre-release truth: implementation exists locally, but release completion remains blocked until the full current-head matrix and exact-head CI pass.

- [ ] **Step 1: Add the public-scan scope assertion and verify RED**

In `test_public_wording_scan_scope_is_public_but_not_tests_or_generated_csvs`, add:

```python
assert "src/portable_research_action_policy.py" in paths
```

Run:

```bash
python3 -m pytest tests/test_public_wording_check.py::test_public_wording_scan_scope_is_public_but_not_tests_or_generated_csvs -q
```

Expected: fail because the new module is not yet in `PUBLIC_SOURCE_FILES`.

- [ ] **Step 2: Add the policy module to release scan and hygiene coverage**

Add `"src/portable_research_action_policy.py"` to `PUBLIC_SOURCE_FILES` in `scripts/public_wording_check.py`. Add the same path to the existing HTML product-candidate tuple in `tests/test_diff_hygiene.py`; the existing `src/` classification should keep that assertion green.

Run:

```bash
python3 -m pytest tests/test_public_wording_check.py tests/test_diff_hygiene.py -q
```

- [ ] **Step 3: Make the documentation contract fail on the old truth**

Replace the stale Priority-7/current-completion assertions in `tests/test_public_v1_release_docs.py` with one focused contract named `test_portable_html_action_repair_docs_route_first_and_remain_release_blocked`. It must require:

```python
blocked = "blocked on bidirectional active/passive action sanitation"
active_lane = "portable HTML action-policy repair is the first executable local release-safety lane"

assert blocked in roadmap
assert active_lane in roadmap
assert active_lane in readme
assert active_lane in product_spec
assert active_lane in methodology
assert "historical implementation evidence only" in continuation
assert "prior synchronization and CI records do not certify the portable HTML repair" in continuation
assert "Priority 7 remains open but is not the active next lane" in roadmap
```

Retain the existing immutable, no-write, no-activation, manual-accessibility, and external-gate assertions. Remove only exact requirements for the obsolete synchronized head/run, `Local feature gate: complete`, and Priority 7 as the current executable lane.

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py -q
```

Expected: the new contract fails against the stale documents.

- [ ] **Step 4: Update all documents to one truthful pre-release state**

Apply these exact concepts without inventing commit, CI, reviewer, source, or market evidence:

- Design status: `approved for implementation on 2026-08-01`.
- ROADMAP HTML gate: `blocked on bidirectional active/passive action sanitation` until Task 4 completes; the portable policy repair is the first executable local lane and Priority 7 remains open but is not active.
- README/Product Spec: the portable download is not release-complete until deterministic active/passive sanitation and current-head verification pass.
- Methodology: the safe boundary removes recognized action language; release completion requires active and modal-passive coverage.
- Dashboard QA: the recorded matrix is pre-repair engineering evidence and must be rerun after the repair.
- Continuation prompt: live repo/PR truth governs; old synchronization/CI anchors are historical and do not certify this repair; route the next local lane to this policy and preserve the external manual-accessibility boundary.

Run:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py tests/test_public_wording_check.py tests/test_diff_hygiene.py -q
make public-wording-check
git diff --check
```

- [ ] **Step 5: Verify protected artifacts, stage exact files, and commit**

```bash
make diff-hygiene-summary
git add -- README.md PRODUCT_SPEC.md ROADMAP.md docs/METHODOLOGY.md docs/DASHBOARD_QA.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md docs/superpowers/specs/2026-08-01-portable-html-action-policy-repair-design.md scripts/public_wording_check.py tests/test_public_wording_check.py tests/test_diff_hygiene.py tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Reconcile portable HTML repair release truth"
```

---

### Task 4: Full Verification, Final Truth, Push, PR, And Exact-Head CI

**Files:**
- Modify after full local evidence only: `ROADMAP.md`, `docs/METHODOLOGY.md`, `docs/DASHBOARD_QA.md`, `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, `tests/test_public_v1_release_docs.py`
- External update: draft PR #113 body/comment; no merge.

**Interfaces:**
- Consumes: all Task 1-3 commits.
- Produces: exact current-head local evidence, aligned remote branch, truthful draft PR, and exact-head CI evidence.

- [ ] **Step 1: Run the complete current-head local matrix**

Run focused checks first, then every applicable release gate:

```bash
python3 -m pytest tests/test_portable_research_action_policy.py tests/test_company_workbench_html.py tests/test_public_wording_check.py tests/test_diff_hygiene.py tests/test_public_v1_release_docs.py -q
python3 -m pytest tests -q
make dashboard-smoke
make research-mode-render-check
make company-workbench-html-browser-check
make research-accessibility-browser-check
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

If an exact target name has changed, inspect the current Makefile and use the current equivalent; do not substitute a generated-data or readiness writer. Record the exact command and result in the SDD ledger.

- [ ] **Step 2: Reproduce the original six phrases against the final code**

```bash
python3 - <<'PY'
from src.company_workbench_html import safe_html_brief_text

expected = "Withheld: reviewer-authored action language is not portable research evidence."
samples = (
    "Shares should be bought now.",
    "The stock should be sold.",
    "A trade should be executed.",
    "The order should be submitted.",
    "The position should be increased.",
    "Long exposure should be opened.",
)
for sample in samples:
    actual = safe_html_brief_text(sample)
    if actual != expected:
        raise SystemExit(f"unsafe output: {sample!r} -> {actual!r}")
print("six modal-passive reproductions withheld")
PY
```

- [ ] **Step 3: Record local verification truth without claiming CI**

Only after Steps 1-2 pass, replace the temporary blocked wording with a truthful state equivalent to:

`Local implementation verified; draft-branch review safety still requires exact-head CI.`

Name the actual implementation commits and actual local test/gate counts. Do not call hosted, source, reviewer, calibration, accessibility, market-fit, or commercial gates complete. Update the documentation contract accordingly.

Run the focused documentation/public/hygiene checks again, stage exact files, and commit:

```bash
python3 -m pytest tests/test_public_v1_release_docs.py tests/test_public_wording_check.py -q
make public-wording-check
make diff-hygiene-summary
git diff --check
git add -- ROADMAP.md docs/METHODOLOGY.md docs/DASHBOARD_QA.md docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md tests/test_public_v1_release_docs.py
make staged-hygiene-check
git diff --cached --check
git commit -m "Record verified portable HTML action policy"
```

- [ ] **Step 4: Re-run the final current-head gates affected by documentation**

```bash
python3 -m pytest tests -q
make dashboard-smoke
make research-mode-render-check
make company-workbench-html-browser-check
make research-accessibility-browser-check
make public-wording-check
make public-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Compare protected hashes with the preflight manifest. Confirm the index is empty and the only unstaged paths are the exact protected 18.

- [ ] **Step 5: Run broad whole-branch review before push**

Generate the SDD final review package from the branch merge-base to HEAD. Dispatch the highest-capability whole-branch reviewer. If findings exist, use exactly one fix wave and one scoped re-review. Do not push with an open load-bearing finding.

- [ ] **Step 6: Push only the approved branch and update draft PR #113**

```bash
git push origin codex/personal-research-mode-mvp
```

Update the PR body/comment with the actual head, local matrix, artifact exclusion, remaining external gates, and the fixed modal-passive reproductions. Keep the PR draft and do not merge.

- [ ] **Step 7: Require exact-head CI**

Wait for the `Commercial Research Beta` workflow on the pushed HEAD. Verify its checked SHA equals `git rev-parse HEAD` and its conclusion is success. If CI fails, diagnose and fix only the current failure, rerun affected local gates, push the repair, update the PR, and wait for the new exact head.

- [ ] **Step 8: Final handoff**

Report repository/PR status, product stage, the repaired issue, tests and browser gates, commit/push/CI state, generated artifacts excluded, external dependencies, remaining roadmap gates, exact next executable step, and whether the branch is safe for review. Do not claim the overall commercial product complete.
