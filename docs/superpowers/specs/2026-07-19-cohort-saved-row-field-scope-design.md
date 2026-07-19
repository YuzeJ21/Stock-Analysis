# Cohort Saved-Row Field-Scope Enforcement Design

## Status

Approved by the owner-supplied independent-audit continuation contract on 2026-07-19. This is the first coherent slice of Priority 2. It covers saved fundamentals, earnings-date, consensus, and trusted-peer rows used by focused-cohort coverage. Price readiness and canonical quarterly-actual packets remain separate follow-up slices.

## Problem

`derive_cohort_evidence()` currently uses one source-level commercial approval as permission for every populated field on a row. The checked-in SEC Companyfacts record approves commercial use only for `revenue`, `shares_outstanding`, and `filing_dates`. If a saved SEC row also contains a margin, free-cash-flow, cash, or debt value, the current cohort code can label that unrelated lane commercially usable without registered field scope.

The same source-level shortcut is reused for earnings dates, consensus, and trusted peers. Technical availability, provenance, commercial rights, and lane-specific registered scope are therefore collapsed into one boolean.

## Selected Scope

Replace the shared permission boolean for these saved-row lanes:

- margins, using the exact populated field among `operating_margin`, `fcf_margin`, and `profit_margin`;
- free cash flow, using `free_cash_flow` or `fcf`;
- cash and debt, reviewed independently as `cash` and `debt`;
- shares outstanding, using `shares_outstanding`;
- filing dates, using `filing_dates`;
- earnings dates, using `earnings_dates`;
- point-in-time consensus, using each populated `revenue_consensus` and `eps_consensus` metric independently;
- trusted-peer evidence, using `trusted_peers` for every trusted relationship row.

Aliases select a local value but never change the exact registered field required for commercial support. Composite or blank source IDs remain unknown.

## Independent Decisions

For every lane, retain four independent facts:

1. technical value availability;
2. provenance presence (`source` plus a durable `source_ref` or SEC accession);
3. exact-source commercial-rights approval;
4. exact registered field scope.

Commercial `usable_now` requires the conjunction applicable to that lane. Missing scope cannot erase technical availability or provenance, and technical availability cannot grant rights. Evidence text names the failed dimension and exact missing field under the existing Advanced cohort coverage surface.

Research mode preserves its current source-backed behavior and does not inherit the commercial license gate.

## Lane Rules

### Margins and free cash flow

Review only fields that are actually populated. A source approved for Revenue or shares cannot unlock a margin or free-cash-flow value. If multiple margin aliases are populated, any individually approved exact field can support the lane; unsupported siblings do not borrow permission.

### Cash and debt

Review cash and debt independently. Both supported values produce `usable_now`; exactly one supported value produces `partial`; neither produces `blocked`. An unsupported populated value remains technically present but commercially unavailable.

### Shares and filing dates

Use the checked-in `shares_outstanding` and `filing_dates` scopes. SEC Companyfacts may support these without supporting margins, FCF, cash, debt, EPS, consensus, earnings dates, or peers.

### Earnings dates

Require an explicit saved date, provenance, approved exact-source rights, and registered `earnings_dates` scope.

### Consensus

Require a fiscal period, a timestamp no later than the review cutoff, provenance, and at least one populated Revenue or EPS consensus value. Each populated metric requires its own registered scope. A Revenue-only source cannot unlock EPS and vice versa. The lane is usable only when every populated metric passes; an empty date-only row is blocked.

### Trusted peers

Every saved trusted relationship row must retain provenance and pass exact-source rights plus `trusted_peers` scope. Candidate rows remain `candidate_context_only` and never enter the trusted decision.

## Output Contract

Keep the existing cohort lane states and frame shape. Strengthen the evidence text for Commercial Research mode so Advanced coverage can distinguish technical, provenance, rights, and field-scope blockers without exposing raw registry records in the primary answer.

No readiness flag, canonical row, source-rights record, forecast, valuation, peer role, or candidate state changes.

## Testing

Tests must prove:

- the checked-in SEC registry supports shares and filing dates but blocks margin, FCF, cash, and debt from the same row;
- an injected source with one approved field cannot unlock sibling lanes;
- cash and debt remain independent;
- Revenue-only and EPS-only consensus scopes do not borrow from each other;
- date-only consensus is blocked;
- trusted peers require every saved row to have `trusted_peers` scope;
- candidate peers remain candidate-only;
- research mode compatibility remains intact;
- dashboard/Advanced cohort contracts retain the truthful lane states and no recommendation language.

## Boundaries

This slice does not approve or fetch a source, edit the registry, validate canonical quarterly actuals, change price readiness, rebuild readiness, generate artifacts, activate consensus, or prove market operation. Priority 2 remains open for adjusted price history and quarterly Revenue/EPS enforcement after this slice.
