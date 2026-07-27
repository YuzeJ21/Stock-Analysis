# Point-in-Time Universe Review History

This internal audit record preserves completed Priority 4 remediation evidence
that no longer belongs in the active roadmap.

It is historical engineering evidence, not current source, hosted, reviewer,
market, or calibration evidence. Current execution state and exit gates remain
in `ROADMAP.md`.

## Review And Remediation Sequence

The second through fourth fresh whole-branch reviews drove the raw-row rights,
cutoff-relative history, publication chronology, immutable bounded-read,
aggregate-budget, and structured-input parser closures.

The fifth fresh whole-branch review confirmed those closures and found three
Important trust-boundary defects: C0/C1 characters in structural identifiers
could render the newline-delimited membership digest ambiguous and forge
public status lines, while manifest creation could predate its cutoff or bound
evidence.

Commits `b2bbd9961` and `c643d066b` remediate those V5 findings locally with
one shared C0/C1 plus Unicode line/paragraph-separator boundary, safe
structural-token rendering, an explicit creation-at-or-after-cutoff manifest
gate, and exact-row chronology against every contract timestamp.

The first independent R7 review found the Unicode separator and
`listing_state_after` bypass gaps; `c643d066b` closes them locally.

The sixth fresh whole-branch review confirmed those closures and found one
remaining Important non-scalar input defect: lone Unicode surrogate code
points could reach public output.

Commit `f143d48ed` rejects Unicode category `Cs` through the shared boundary
and defensively ASCII-escapes it while valid supplementary-plane scalars
remain deterministic.

The seventh fresh whole-branch review confirmed the V6 correction and found
four further trust-boundary defects (two Critical, one Important, and one
Minor): duplicate JSON/YAML mapping keys could silently change manifest and
rights meaning; invalid or unresolved successor and listing-state evidence
could authorize stale original-member digests; malformed CSV headers could
discard contract bodies and continue; and non-RFC3339 manifest or policy
timestamps were accepted.

The local seventh-review remediation rejects duplicate keys at every mapping
depth, requires strict RFC3339 UTC manifest and policy timestamps with at most
six fractional-second digits, stops malformed headers as package-level
input-identity failures, and enforces explicit policy/event/listing-state,
successor-identity, and membership-consistency gates without inferring or
repairing a successor or membership.

An independent scoped re-review then confirmed the four original findings and
the two compatibility regressions were addressed.

The eighth fresh whole-branch review then found three Critical, nine Important,
and two Minor defects across sub-microsecond ordering, event-time identity,
listing chronology and rights, walk-forward bootstrap aggregation,
identity/action reconciliation, eligible provenance, package-contained bounded
reads, manifest type handling, standalone rights loading, and literal-safe Make
arguments.

Remediation 9A through 9G closed every finding test-first. Independent scoped
re-reviews confirmed no remaining Critical or Important finding in each
corrected scope; the two Minor contracts now reject identical issuer/security
IDs and recursively freeze manifest semantics.

Freeze reconciliation consolidated 21 overlapping remediation test files into
six domain suites and one shared fixture module, removed one exact duplicate
plus cross-remediation private imports, and closed five additional local
correctness gaps: ambiguous parents cannot authorize forks; pre-action cutoffs
do not poison later required coverage; decision-consumed listing-state evidence
is retained in eligible provenance; manifest nesting is explicitly bounded;
and structural source IDs cannot forge status output.

Full branch verification at freeze reconciliation is 4,084 passing tests, one
environment-limited socket test skipped, and one existing dependency
deprecation warning.

The final fresh whole-slice review found one Important cutoff-relative event
regression; it was reproduced, fixed, and confirmed closed with no remaining
Critical or Important issue. The consolidated package was synchronized at
`69c49968e77bfd55fa259695089e1f34ac2fddfb`, and exact-head GitHub Actions run
`30185232040` passed the full test, dashboard-startup, Personal Research
render, public-wording, PR-range generated-artifact hygiene, and whitespace
matrix.

Real-data evidence remains pending; Priority 4 remains externally incomplete.

## Resource And Input Boundaries

Local resource budgets for one supplied package: preview sample 100 rows;
manifest 1 MiB; each contract CSV 32 MiB; four contract snapshots combined 64
MiB; source-rights registry 4 MiB; declared rows 250,000 per contract; package
traversal 32 entries.

Duplicate JSON/YAML mapping keys and malformed contract headers also fail
nonzero, traceback-free, and write-free through the direct validator and
CLI/Make boundaries.

These local bounds do not prove scale, hosted reliability, or market
readiness.

No permitted independently reviewed real dataset, accepted expected
count/digest, or source-rights proof is on record.
