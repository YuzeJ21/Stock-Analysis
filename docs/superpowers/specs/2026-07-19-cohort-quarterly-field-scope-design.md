# Cohort Quarterly Field-Scope Design

## Problem

Commercial focused-cohort coverage builds quarterly Revenue and EPS states from
technically valid trend packets. It does not yet require every retained source
row for each metric to pass the exact source-rights and supported-field review.
That can reuse a source's Revenue permission for EPS even when EPS is outside the
registered commercial scope.

## Decision

Derive independent commercial reviews for quarterly Revenue and quarterly EPS
from the accepted canonical `QuarterlyActual` rows. A metric is commercially
usable only when it has at least one populated row and every populated row has:

- a source, source reference, and retrieval timestamp;
- an exact source whose commercial use is approved; and
- the matching registered field scope (`revenue` or `eps`).

The commercial review is conjunctive with the existing trend-packet state. A
commercial blocker therefore fails the lane closed even when a technical packet
could otherwise render a comparison. Revenue and EPS remain independent.

Research mode keeps the existing packet-only behavior. This slice does not
change EPS split-basis policy, canonical-loader rejection policy, Q4 policy,
consensus readiness, calibration, or any generated artifact.

## Display boundary

The primary cohort answer remains a compact lane state. Exact source-rights or
field-scope blockers remain in the evidence text shown under Advanced. No value,
forecast, probability, recommendation, or synthetic fallback is created.

## Verification

- Prove Revenue can remain usable when its exact source is approved for Revenue.
- Prove EPS blocks independently when that same source lacks EPS scope.
- Prove unknown/unapproved and mixed-source metric rows fail closed.
- Prove Research mode retains the existing packet behavior.
- Prove the dashboard passes accepted canonical actuals into the commercial
  evidence derivation without writing or repairing the ledger.
