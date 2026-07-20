# Canonical Quarterly Ledger Fail-Closed Design

## Problem

The canonical quarterly-actual CSV loader retains valid rows while reporting
invalid rows separately. Dashboard trend and cohort composition currently pass
only the accepted rows downstream. A partially rejected canonical ledger can
therefore produce apparently usable quarterly evidence.

## Contract

- Keep the loader non-writing and audit-friendly: it may return accepted rows
  together with row-numbered rejection evidence.
- Add one load-result-aware packet boundary. If any canonical row is rejected,
  do not build a quarterly trend from any accepted row in that file.
- Treat the canonical ledger as one integrity unit for dashboard consumption:
  one rejected row blocks Revenue, EPS, and supplemental quarterly trend use for
  every ticker until the ledger is corrected and reviewed.
- Carry row number and validation reason into the blocked packet and display
  that evidence only in the existing Advanced quarterly evidence expander.
- The focused cohort must not derive quarterly commercial evidence from the
  accepted subset of a partially rejected canonical ledger.
- Missing ledgers remain empty/blocked. No rejected row is repaired, inferred,
  promoted, written, or copied.

## Boundaries

This slice does not change SEC staging, Q4 policy, EPS split-basis policy,
readiness, canonical data, source rights, or generated artifacts. It does not
claim that a fully parseable ledger has been externally verified.
