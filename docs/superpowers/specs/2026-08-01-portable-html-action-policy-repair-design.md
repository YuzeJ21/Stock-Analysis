# Portable HTML Action Policy Repair Design

**Status:** proposed for written-spec review

## Decision

Replace the Company Workbench HTML brief's forward-only action-language scan
with one deterministic, fail-closed portable-research policy that recognizes
both active and modal-passive transaction grammar. Keep the current
`safe_html_brief_text(value)` API as the renderer boundary, but move the policy
implementation into a pure module so the HTML snapshot/renderer no longer owns
an expanding natural-language grammar.

The repair is a release-safety slice. It does not add an investing feature,
recommendation, ranking, order workflow, current-market claim, data source,
readiness refresh, or generated repository artifact.

## Current Problem

The local repair branch correctly closes the original whole-branch review
findings around secrets, paths, cutoff handling, scenario bridges, provenance,
empty catalyst state, and many active action-language variants. Its current
scanner still searches action predicate before endpoint. It therefore returns
these modal-passive instructions unchanged:

- `Shares should be bought now.`
- `The stock should be sold.`
- `A trade should be executed.`
- `The order should be submitted.`
- `The position should be increased.`
- `Long exposure should be opened.`

This violates the approved portable-brief contract even when the source is a
reviewer-authored field. Portable HTML can leave the workspace authorization
context, so transaction-equivalent prose must never be emitted as research
evidence.

The existing implementation also places hundreds of policy lines inside
`src/company_workbench_html.py`, although the approved HTML design assigns that
module only snapshot construction and deterministic rendering. Continuing the
five-round patch loop would deepen that architectural drift.

## Goals

1. Withhold active and passive recommendation, transaction, execution,
   directional-exposure, and position-lifecycle language deterministically.
2. Preserve ordinary research, accounting, classification, record, coverage,
   and methodology prose that happens to contain an overloaded action word.
3. Apply one policy at snapshot construction and renderer defense-in-depth so
   unsafe source text is absent from snapshot representations, fragments,
   complete documents, and downloaded bytes.
4. Preserve independent readiness states and the existing fixed withheld
   message.
5. Restore truthful roadmap, methodology, QA, continuation, and PR status only
   after current-head verification succeeds.

## Non-goals

- No LLM, external moderation service, probabilistic classifier, or provider
  dependency.
- No attempt to determine whether an instruction is good, bad, suitable, or
  negated.
- No expansion into allocation, position sizing, portfolio management,
  brokerage, order routing, auto-trading, or live holdings.
- No source refresh, readiness rebuild, CSV/JSON/report generation, or broad
  coverage loop.
- No change to deterministic forecasts, scenarios, readiness calculations, or
  trusted-evidence rules.

## Alternatives Considered

### 1. Add one reverse scan inside `company_workbench_html.py` — rejected

This is the smallest diff, but it would be a sixth patch in the exhausted loop
and would keep policy, snapshot construction, and rendering coupled. It would
also make future false-positive controls harder to test independently.

### 2. Extract a bidirectional deterministic policy module — selected

Create `src/portable_research_action_policy.py` and move the tokenizer,
normalization, action families, exact safe boundaries, classification
exclusions, and semantic scans into it. Add a family-specific modal-passive
scan while preserving the public HTML sanitizer API. This is locally
testable, offline, explainable, and fail-closed.

### 3. Replace reviewer prose with controlled templates — deferred fallback

Controlled templates would be safest but would remove useful thesis, evidence,
catalyst, risk, invalidation, and outcome context. Use this only if the selected
policy cannot pass the adversarial and safe-control corpus without unacceptable
false positives.

### 4. Use an NLP or LLM moderation service — rejected

An external classifier would be nondeterministic, add data-transmission and
availability dependencies, and weaken offline reproducibility. It is not an
acceptable release boundary for the portable brief.

## Architecture

### Pure policy module

`src/portable_research_action_policy.py` owns:

- NFKC normalization, case folding, ignorable-format removal, clause splitting,
  and tokenization;
- action-family definitions and exact classification/reference exclusions;
- standalone prohibited terms and fixed prohibited phrases;
- active `predicate -> endpoint` detection;
- passive `endpoint head -> modal/auxiliary -> family participle` detection;
- a pure `contains_portable_action_language(value: str) -> bool` entry point.

The module reads no files, imports no dashboard state, performs no writes, and
has no HTML dependency.

### HTML compatibility boundary

`src/company_workbench_html.py` retains `safe_html_brief_text(value)` and the
fixed output:

`Withheld: reviewer-authored action language is not portable research evidence.`

The wrapper keeps the existing primitive-type, control-character, secret,
path, URL, trimming, and HTML-escaping behavior. It calls the pure action policy
before escaping. `_html_brief_text` continues to call the same wrapper as a
defense-in-depth boundary for manually constructed snapshots.

No caller may bypass this wrapper with raw HTML or a second permissive sanitizer.

## Deterministic Grammar

The policy processes each clause in this order:

1. Normalize Unicode with NFKC and case folding.
2. Remove ignorable formatting characters without joining previously separate
   semantic tokens into an allowed phrase.
3. Tokenize letters/numbers and retain bounded separator metadata.
4. Remove only the existing exact non-action classifications:
   `available for sale`, `held for sale`, and `held to maturity`.
5. Remove only the existing exact research-only boundaries:
   `no recommendation`, `no buy sell instruction`, `no broker integration`,
   and `not investment advice`.
6. Detect standalone prohibited terms and fixed prohibited phrases.
7. Detect active action-family predicate followed by a compatible endpoint
   within the existing bounded token window.
8. Detect passive action-family endpoint head followed by a supported modal or
   auxiliary chain and a compatible action participle.

Supported modal/auxiliary chains include the ordinary combinations built from
`must`, `should`, `can`, `could`, `may`, `might`, `will`, `would`, or `shall`
with `be` or `get`, plus directly inflected passive constructions where the
family match is unambiguous.

The nominal endpoint must be the semantic head immediately before the
modal/auxiliary chain, apart from a small explicitly tested modifier set. This
keeps these controls available:

- `The position estimate should be increased.`
- `The trade record should be ordered by date.`
- `The equity method should be held constant.`
- `Securities are held to maturity.`
- `Assets are available for sale.`

`Exposure` participates only in the position/directional family. It is not a
generic security or execution endpoint.

Negation does not make an action construction portable. For example, `Shares
should not be bought` remains withheld because the portable artifact must not
carry transaction instructions or their inversions. Only the four exact fixed
research-only boundaries above are removed before scanning.

## Data Flow

```text
reviewer/source text
        |
        v
snapshot field helper
        |
        v
safe_html_brief_text
  | secret/path/URL checks
  | portable action policy
  | HTML escaping
        |
        v
immutable snapshot
        |
        v
renderer defense-in-depth (_html_brief_text)
        |
        +--> in-app fragment
        +--> complete offline HTML document
        +--> UTF-8 download bytes
```

Unsafe input becomes only the fixed withheld message. It cannot be partially
redacted, rewritten into advice, logged as a new evidence record, or used to
change a scenario/readiness state.

## Error Handling

- Unsupported value types, control characters, secrets, paths, and URL-shaped
  portable text retain the existing empty-output behavior.
- Recognized action language returns the fixed withheld message.
- Malformed or ambiguous action constructions fail closed when they match a
  prohibited family; safe exceptions must be exact and covered by positive
  tests.
- The policy never raises a user-visible exception for ordinary text. A coding
  error remains a test/release failure; it must not be converted into permissive
  output.

## Test Strategy

### Pure policy unit tests

Add `tests/test_portable_research_action_policy.py` with table-driven coverage
for:

- the six exact modal-passive leaks;
- every supported modal and `be`/`get` combination;
- active/passive inflections for security, execution, position, covering, and
  directional families;
- punctuation, numeric qualifiers, Unicode hyphens, NFKC equivalents, and
  ignorable-format adversaries;
- clauses, coordination, and negation;
- the safe research/accounting/reference controls listed above;
- the four exact boundary phrases and three classification phrases;
- deterministic repeatability and no file/data access.

### HTML integration tests

Extend `tests/test_company_workbench_html.py` to inject passive language through
every portable free-text field family. Assert the original unsafe text is absent
from:

- `repr(snapshot)`;
- rendered in-app fragment;
- complete HTML document;
- UTF-8 download bytes.

Assert the fixed withheld message is present, no independent field state is
promoted, safe control prose is preserved and escaped, and current public APIs
and filenames remain unchanged.

### Release-policy tests

- Add the new module to `scripts/public_wording_check.py` coverage and update
  `tests/test_public_wording_check.py`.
- Add it to product-candidate/diff hygiene assertions.
- Update documentation contract tests so they require an honest blocked state
  until the complete current-head matrix passes, then require the verified
  completion wording and exact evidence.

## Documentation And Roadmap Truth

Before implementation is presented as complete:

- change the current ROADMAP HTML gate from `complete` to `blocked on
  bidirectional active/passive action sanitation`;
- make this repair the first executable local lane;
- remove obsolete `Priority 7` and old synchronization claims from README,
  Product Spec, Methodology, Dashboard QA, the continuation prompt, and their
  contract tests;
- record the six local commits as legitimate but not release-safe evidence;
- update draft PR #113 with the current local/remote distinction and do-not-
  merge condition.

Only after all gates pass may those documents say the HTML gate is complete.

## Verification And Release Gates

The coherent repair is accepted only when all current-head evidence passes:

1. New pure-policy unit tests.
2. Full `tests/test_company_workbench_html.py`.
3. Relevant dashboard/workflow integration selection.
4. `python3 -m pytest tests -q`.
5. Dashboard smoke and all route/render/HTML-browser/responsive-accessibility
   checks applicable to the feature.
6. Public wording, public package/release, pilot, and content-fingerprint gates.
7. Diff hygiene, whitespace, exact generated-artifact hash comparison, and
   staged hygiene after exact staging.
8. One coherent commit, pushed only to
   `codex/personal-research-mode-mvp`.
9. Draft PR #113 remains open/draft and exact-head CI passes.

No readiness rebuild, broad refresh, CSV/JSON/report/sample-report/screenshot/
timing generation, merge, or public deployment is part of this slice.

## Acceptance Criteria

- All six reproduced modal-passive phrases are withheld everywhere.
- The adversarial active/passive corpus passes without weakening existing
  secret/path/URL and provenance safeguards.
- Safe research/reference/accounting controls remain visible.
- The policy is isolated from snapshot construction and rendering.
- No portable field bypasses the policy.
- No generated working-data artifact changes beyond the protected pre-existing
  dirty set, and none is staged.
- Full local gates and exact-head CI pass.
- ROADMAP, product documentation, continuation contract, and draft PR report the
  same current truth.
- The branch is not called review-safe until all criteria above have direct
  current evidence.

## Rollback

If the extracted policy cannot pass both the adversarial and safe-control
corpora, disable the HTML preview/download entry point behind a fixed withheld
state and return to the controlled-template alternative. Do not restore the
forward-only scanner or ship a partially certified portable brief.
