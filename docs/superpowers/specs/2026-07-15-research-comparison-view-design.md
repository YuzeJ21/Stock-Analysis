# Research Comparison View Design

## Purpose

Upgrade the existing operator-only selected-ticker tray into a two-to-three-company research comparison. The comparison helps a reviewer see which evidence is usable, which inputs are blocked, and which reviewed catalysts or risks exist without ranking companies or producing an action.

## Placement

Use the existing `Advanced: selected review tray` in Stock Selector. Do not add a new page, navigation item, or public first-viewport panel. The tray remains optional and collapsed by default.

## Approaches Considered

1. **Recommended: evidence matrix in the existing selected review tray.** Reuse selector readiness rows and profile-scoped Research Thesis Journal state. This connects existing surfaces and avoids duplication.
2. **Dedicated comparison page.** More space, but it fragments the five-page workflow and repeats selector/report content.
3. **Automatic ranking table.** Compact, but it violates the research-only boundary and encourages false precision from uneven readiness.

Use approach 1.

## Contract

Selection is limited to two or three unique tickers and preserves user order. Each ticker column shows:

- asset type and research state;
- price, fundamentals, DCF, and trusted-peer readiness;
- supported analysis now;
- blocked or missing inputs;
- next proof step and proof freshness;
- reviewer-authored catalysts and risks from the selected profile's append-only journal.

Missing readiness or journal fields remain `Not available` or `No reviewed journal evidence`. Candidate peer context cannot display as trusted-peer readiness. The view never calculates a score, winner, rank, recommendation, expected return, or transaction instruction.

## Data Flow

`stock_selector_queue_frame` carries explicit readiness booleans from the selected profile's readiness row. `src/research_comparison.py` validates the selection and creates immutable company columns plus a display matrix. Dashboard integration loads journal state only for selected tickers and only after the Advanced tray is opened.

## Error Behavior

- Fewer than two tickers: show a neutral selection prompt and no matrix.
- More than three: reject rather than truncate silently.
- Duplicate tickers: reject.
- Cross-profile journal rows: excluded by the existing journal loader.
- Missing source/readiness evidence: shown as missing, never inferred.

## Verification

Tests cover selection constraints, order, readiness-state mapping, trusted-peer separation, journal catalyst/risk extraction, missing evidence, prohibited language, collapsed placement, and public-flow preservation. Full dashboard and public release gates must pass.
