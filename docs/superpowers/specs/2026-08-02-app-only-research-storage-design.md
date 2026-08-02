# App-Only Research Storage And No-Write Computation Design

## Status

The A+C direction was approved on 2026-08-02. This written specification is
awaiting user review before an implementation plan is created.

## Decision

Adopt a hybrid local architecture:

- ordinary research exploration and every derived calculation remain in memory;
- only explicitly confirmed research records are persisted;
- persisted records use one application-managed local SQLite database outside
  the repository;
- normal Research Desk, Discover, Company Workbench, and Monitor use requires no
  CSV, JSON, HTML, report, or spreadsheet file generation or download;
- Python remains the authoritative calculation and validation layer, while HTML
  remains an in-app presentation layer; and
- a provider-neutral storage boundary allows a later approved hosted adapter to
  replace local SQLite without changing the research workflow or domain rules.

This is the selected A+C approach. It removes user-managed file operations now
without pretending that a hosted private environment already exists.

Once approved and implemented, this design supersedes only two earlier local
decisions: CSV-ledger persistence for newly confirmed research records and the
placement of Company Workbench downloads in the ordinary research flow. The
existing preview-receipt, append-only, safe-HTML, independent-readiness,
provenance, and research-only contracts remain authoritative. Until the
corresponding implementation slice is verified, the current CSV and download
behavior remains the truthful shipped behavior.

## Current Repository Truth

The current product already performs most valuation, scenario, trend, review,
readiness, and HTML-brief composition in Python memory. Company Workbench also
has a preview-and-confirm authoring flow for thesis, evidence, catalyst, and
outcome records. Scenario Lab is session-only and does not write files.

The remaining problem is architectural coupling:

- all four Personal Research routes still load broad legacy output tables or
  saved readiness artifacts before rendering;
- Company Workbench exposes HTML and audit-data downloads in the ordinary
  workflow;
- confirmed research records append to several CSV ledgers;
- readiness and composite operator commands can rewrite many derived snapshots,
  including a canonical universe file; and
- Workbench report and Scenario Lab session identities are not fully bound to
  profile, provider, source snapshot, method version, and input identity.

The pre-existing modified generated files are protected user working data. This
design does not authorize restoring, deleting, staging, committing, or replacing
them.

## User Outcome

A researcher can open the application and complete the full workflow:

`Research Desk -> Discover -> Company Workbench -> Monitor`

without locating, editing, generating, downloading, or opening a spreadsheet,
CSV, JSON, or report file.

Filters, sliders, provisional notes, queue construction, scenario calculations,
charts, readiness summaries, and rendered HTML are session-only. Only an exact
eligible record that passes preview and explicit confirmation becomes durable.
Closing or refreshing the application therefore cannot create background file
churn.

When the researcher explicitly saves a validated record, the application owns
the persistence operation and verifies the durable result before claiming
success. The user manages research concepts, not files.

## Approaches Considered

### A+C. In-memory computation plus one app-managed local database — selected

This preserves research history, removes user-managed files from the normal
workflow, works without a hosted account, and provides a narrow migration path
to hosted storage.

### B. Hosted private database now — deferred

This is the only option that physically keeps durable research data off the
local computer. It is deferred because the repository does not have verified
hosted authentication, workspace isolation, audit storage, retention, backup,
rollback, monitoring, incident response, or operating ownership. Selecting it
now would turn an executable local product improvement into an externally
blocked hosting program.

### C. Session-only application — rejected as the complete solution

Session-only operation is correct for provisional work, but using it for every
record would discard thesis history, evidence lineage, catalysts, outcomes, and
saved scenarios. That would remove the product's strongest evidence-governance
advantage.

## Scope

The local A+C foundation covers:

1. no-write defaults for derived computation;
2. route-native, in-memory Personal Research views;
3. correct session and cache identity;
4. one provider-neutral research-record storage interface;
5. one local SQLite implementation for explicitly confirmed records;
6. an explicit, idempotent legacy-ledger import path;
7. in-app HTML presentation with no normal-flow download requirement; and
8. protected-artifact and fail-closed regression evidence.

## Non-Goals

This design does not:

- migrate canonical market, filing, fundamentals, price, consensus, benchmark,
  peer, or source-rights inputs into SQLite;
- fetch, refresh, broaden, or fabricate source data;
- make stale readiness current or promote any readiness state;
- supply point-in-time consensus, reviewed peers, calibration, source rights,
  independent workflow evidence, or hosted operating evidence;
- implement authentication, accounts, multi-user workspaces, cloud storage,
  synchronization, collaboration, or backup;
- duplicate valuation or research logic in browser JavaScript;
- add probabilities, recommendations, rankings, position sizing, transactions,
  brokerage, order routing, auto-trading, or post-earnings price predictions;
- delete or rewrite existing legacy ledgers or generated working artifacts; or
- treat synthetic fixtures, candidate context, or an HTML view as trusted
  evidence.

Canonical source inputs remain source inputs until a separately approved source
repository migration exists. The objective here is to remove redundant derived
artifacts and user-managed persistence from ordinary product operation, not to
hide or weaken data lineage.

## Architecture

### 1. Authoritative in-memory computation

Existing Python domain modules remain authoritative. Dashboard routes request
immutable research snapshots from route-focused composition functions. Those
functions may read permitted canonical inputs and the selected research-record
store, but they return values and never materialize derived files.

Readiness, queue, valuation, scenario, trend, review, and HTML composition
functions default to no-write behavior. A route render, filter change, slider
change, form validation, recalculation, or HTML preview must not create a
directory or modify a file.

Browser JavaScript may support presentation-only behavior such as chart pan or
zoom. Any value shown as a canonical research result must be computed and
validated by Python. The browser must never become an independent valuation,
readiness, forecast, probability, or evidence engine.

For heavier calculations, the UI uses a form or explicit `Recalculate` action
so several control changes produce one deliberate Python computation instead
of multiple page-wide reruns.

### 2. Route-native research snapshots

The shared Personal Research shell must not load legacy pipeline or monthly
output collections merely to render its header. Each route requests only the
inputs required for its answer:

- **Research Desk** composes the workflow answer and lane states in memory.
- **Discover** uses the strict in-memory daily research queue and focused-cohort
  evidence. It does not require generated research decisions or a generated
  final watchlist as a fallback.
- **Company Workbench** composes the selected-company report, scenarios,
  records, and static HTML fragment in memory.
- **Monitor** compares saved baselines and reviewed records in memory without
  generating a change-snapshot file.

If a legacy derived file is absent, the route still renders. A missing required
canonical input produces the existing truthful empty, stale, partial, excluded,
or withheld state plus an in-app Data Health path. It must not tell an ordinary
research user to edit a repository CSV or run a command-line repair sequence.

### 3. Session and cache identity

A report cache entry is reusable only when all of these match:

`profile_key + snapshot_identity + ticker + provider + method_version`

Scenario controls and provisional scenario results are additionally bound to
the exact scenario input identity. When the underlying source snapshot or model
identity changes, the application starts a fresh scenario state. It must not
silently carry old assumptions into a new baseline.

Session state is volatile UI state, not audit evidence. A session object cannot
prove that a record was saved and cannot activate readiness.

### 4. Provider-neutral persistence boundary

Add a small `ResearchRecordStore` protocol between validated domain records and
physical storage. It exposes typed operations rather than SQL or file paths to
the dashboard:

- list records by exact workspace, profile, ticker, and record kind;
- append one receipt-matched thesis, evidence, catalyst, or outcome record;
- append one explicitly saved scenario;
- load one exact record for post-save verification; and
- inspect storage schema and migration state.

There is no generic overwrite operation for research records. Thesis, evidence,
catalyst, outcome, and saved-scenario history remains append-only. Corrections
use explicit revision or supersession lineage.

The dashboard continues to call the existing authoring composition layer. That
layer owns validation, preview receipts, exact-record reconstruction, reference
checks, and stale-preview protection; it delegates the final append and reload
to the store. The dashboard never opens SQLite or a legacy ledger directly.

The interface contains no SQLite-specific types. A future hosted adapter must
implement the same behavioral contract and must invoke the existing
deny-by-default workspace authorization decision before every hosted read or
write.

### 5. Local SQLite adapter

The local adapter uses Python's standard-library `sqlite3` module. It stores one
logical database named `research.sqlite3` in the operating system's private
application-data directory, outside the Git repository. An explicit
`STOCK_RESEARCH_APP_DATA_DIR` override is permitted for tests and operator-owned
local configuration; the value and resulting database remain outside Git.

The path resolver follows platform conventions:

- macOS: `~/Library/Application Support/Stock Research Command Center/`;
- Windows: `%LOCALAPPDATA%/Stock Research Command Center/`; and
- Linux: `${XDG_DATA_HOME:-~/.local/share}/stock-research-command-center/`.

The directory and database are created lazily on the first successful explicit
save, not during application startup, route rendering, validation, preview, or
calculation. File permissions are restricted to the current user where the
platform supports that operation. SQLite may create short-lived transactional
sidecar files inside the same app-managed directory; they are implementation
details, never repository artifacts or user workflow objects.

The read side opens an existing database in read-only mode. A missing database
returns the empty local-store state without creating the directory, database,
journal, or lock file. Local mode uses one fixed internal workspace identity,
`local-personal`, which is not editable in the UI; the adapter rejects a request
for any other workspace. Tests may inject a different exact workspace identity
only through the adapter constructor.

The local adapter is a single-user, single-workspace convenience boundary. It
does not claim encrypted application storage, authenticated identity, hosted
workspace isolation, synchronization, backup, or multi-user security. Device
protection remains an operating-system responsibility until a hosted adapter is
separately approved and verified.

### 6. Durable record envelope

Every stored row contains a small indexed envelope plus a canonical validated
payload:

- schema version;
- workspace ID, profile key, normalized ticker, and record kind;
- stable record ID;
- canonical payload JSON and SHA-256 payload digest;
- preview-receipt digest and confirmation time;
- source, publication, retrieval, as-of, cutoff, and rights references when the
  domain record contains them;
- method/model version and input identity for a saved scenario;
- revision or supersession reference when applicable; and
- created-at timestamp and explicit reviewer value supplied by the existing
  record contract.

The adapter does not invent missing provenance, timestamps, rights, reviewers,
or evidence. Domain validation happens before storage, and database constraints
enforce uniqueness, exact scope, append-only behavior, and valid references.

Payload JSON is storage representation, not a generated report. It lives only
inside the application database and is never written as a repository JSON file.

Schema version 1 contains exactly three storage areas:

- `app_schema`, containing the installed schema version;
- `research_records`, containing the indexed envelope and canonical payload;
  and
- `migration_receipts`, containing one idempotency record for each confirmed
  legacy-ledger import.

`research_records` uses a composite identity of workspace, profile, ticker,
record kind, and record ID. A unique workspace-scoped preview-receipt digest
prevents a confirmed preview from being appended twice. Optional parent and
supersession identities include the referenced record kind and use composite
foreign keys that include workspace, profile, and ticker, so a reference cannot
cross scope. Foreign-key enforcement is enabled on every connection. Supported
record kinds are exactly `thesis`, `evidence`, `catalyst`, `outcome`, and
`saved_scenario`. The schema adds no mutable research-content table and no
delete or update path for an existing research record.

An unreadable database or unsupported schema version fails closed as
`storage_unavailable` or `storage_upgrade_required`. The adapter never repairs,
replaces, truncates, or silently recreates a database. Any future schema change
requires a separately tested, forward-only transactional migration.

### 7. Transaction and confirmation behavior

A confirmed save uses one transaction:

1. resolve the exact workspace and store;
2. revalidate the draft and preview receipt;
3. verify referenced and superseded records inside the same transaction;
4. append exactly one record;
5. commit;
6. reload the exact record from the store; and
7. report success only if the reloaded digest matches the confirmed digest.

A write transaction acquires its write reservation before rechecking references
and uses database uniqueness as the final double-submit guard. A duplicate
receipt, duplicate record, stale preview, changed input identity, invalid
reference, or pre-commit storage error writes nothing. The UI must not silently
retry, append to a CSV fallback, claim success from session state, or mutate
another record.

If the process cannot determine whether a commit succeeded, it returns the
existing `save_pending_reload` state with the exact record identity. It then
allows only a read-side reconciliation; it never states that nothing was saved
and never invites a blind duplicate retry.

If SQLite is unavailable, the application remains usable for ephemeral
research. Save actions are disabled or return `storage_unavailable` with an
explicit statement that nothing was saved. Existing trusted records must not be
replaced by an empty database or fabricated recovery state.

### 8. Legacy-ledger transition

Existing CSV ledgers remain read-only historical inputs until explicitly
migrated. The application provides an Advanced, in-app `Migrate research
history` flow with the same preview-and-confirm discipline:

1. discover only the existing supported ledgers for the selected profile;
2. validate every row through its current domain loader;
3. display counts, blockers, exact source-ledger digests, and the destination
   database identity without writing;
4. require explicit confirmation;
5. import valid records in one transaction; and
6. record an idempotent migration receipt keyed by source digest and schema
   version.

A malformed ledger blocks that ledger's import. The importer does not skip bad
rows, repair data, delete the source, or produce a replacement CSV. Repeating an
accepted migration is a no-op with a verified receipt, not a duplicate append.

After a ledger has a verified migration receipt, the application reads those
records from SQLite and all new saves go only to SQLite. Before migration,
legacy records may be displayed read-only with a clear legacy-source label; a
database failure never redirects a confirmed save back to CSV.

### 9. In-app HTML and export boundary

Company Workbench continues to build the approved static HTML fragment in
memory from already-computed Python results. The fragment is presentation only:
it is not a database, source, audit record, calculation engine, or readiness
artifact.

The ordinary Company Workbench flow removes `Download HTML Research Brief` and
`Download Audit Data`. The primary experience displays the complete brief,
provenance, blockers, and methodology in the application, with technical detail
under Advanced.

The existing HTML export remains only under an explicitly opened
`Advanced -> Optional exports` boundary for a user who deliberately wants a
portable copy. Preparing its bytes must remain pathless and in memory; only the
browser's user-initiated download may create a file. The Audit JSON download is
removed from Personal Research; the same audit details remain readable under
Advanced without creating a file.

No route, preview, test, smoke check, or release check may automatically invoke
an export.

### 10. Generated-artifact boundary

Derived readiness, coverage, queue, status, report, and change-snapshot objects
are computed in memory by default. Library builders default to no-write.
Composite validation and dashboard targets must not call materializing writers.

If an operator still needs a frozen derived snapshot for a separately approved
review, materialization uses a clearly named explicit command, requires an
explicit confirmation flag, and writes one non-duplicated set only under an
ignored app/operator directory: `outputs/local/derived/<profile>/`.
Materialization cannot repair or rewrite canonical inputs. Compatibility copies
in tracked `data/` and duplicate copies in tracked `outputs/` are not produced.

Slice 1 replaces the current command boundary as follows:

- `make readiness-preview TOP_N=...` remains the stdout-only no-write preview;
- `make readiness` becomes a non-writing deprecated guard that points to the
  preview or explicit materialization command;
- `CONFIRM_MATERIALIZE=1 make readiness-materialize PROFILE=...` is the only
  readiness snapshot writer; and
- dashboard, smoke, status, onboarding, daily, pipeline, test, and verification
  targets never call the materialization command.

The materializer must never mutate `data/universe_master.csv` or any other
canonical input as a side effect of readiness computation.

## UI Behavior

The visible application changes are intentionally small:

- the four Personal Research routes load and operate without legacy derived
  output files;
- missing data routes to an in-app Data Health action instead of file or shell
  instructions;
- Scenario Lab recalculation is explicit and source-snapshot-bound;
- Company Workbench shows its HTML brief directly and removes downloads from
  the primary path;
- saving a reviewed record is the only ordinary action that creates durable
  local state; and
- save success includes the record ID and durable verification, while definite
  pre-commit failures say plainly that nothing was saved and an uncertain commit
  uses `save_pending_reload`.

No new top-level route is required. Storage migration and optional export stay
under Advanced so technical mechanics do not displace the primary research
answer.

## Research And Safety Boundaries

The change preserves all independent readiness states for actuals, consensus,
Revenue, EPS, valuation, catalysts, outcomes, backtesting, and calibration.

- Real-company Earnings Nowcast remains blocked without permitted point-in-time
  consensus.
- Numerical Beat/Miss probability remains withheld without valid calibration
  evidence.
- EPS split basis remains unverified without explicit proof.
- Q4 actuals require explicit SEC-filed Q4 table evidence.
- Synthetic fixtures remain test-only.
- Empty valuation, catalyst, outcome, peer, consensus, and historical ledgers
  display empty or withheld states, never fabricated content.
- Candidate context cannot modify deterministic calculations or become trusted
  evidence.
- Storage success cannot promote readiness, alter a forecast, or create an
  investment conclusion.

## Delivery Slices

The implementation is divided into coherent, independently verified slices.

Each slice receives its own test-first implementation plan, verification, exact
commit set, push, draft-PR update, and exact-head CI evidence before the next
slice begins.

### Slice 1 — No-write derived-artifact boundary

- make the readiness and universe library builders no-write by default;
- prevent readiness from repairing canonical universe inputs;
- introduce the explicit ignored-directory readiness materializer and convert
  `make readiness` into the non-writing guard described above;
- remove generated writers from composite validation targets; and
- add protected-path byte-manifest tests for default builder, dashboard, smoke,
  test, status, onboarding, daily, pipeline, and verification paths.

### Slice 2 — Route-independent Personal Research workflow

- remove broad legacy output loading from the Personal Research shell;
- make all four routes render fail closed when legacy `outputs/*.csv` files are
  absent; and
- replace ordinary file and command-line recovery instructions with in-app Data
  Health actions.

### Slice 3 — Correct in-memory identity

- bind report cache state to profile, snapshot, ticker, provider, and method;
- bind Scenario Lab state to exact source/input identity;
- add explicit recalculation for heavier scenario work; and
- prove source changes cannot reuse stale report or assumption state.

### Slice 4 — App-managed research-record storage

- introduce `ResearchRecordStore` and the local SQLite adapter;
- preserve existing preview, receipt, validation, and append-only contracts;
- migrate confirmed thesis, evidence, catalyst, outcome, and saved-scenario
  writes to the adapter; and
- verify every success by an exact durable reload.

### Slice 5 — App-only workflow completion

- add the in-app legacy-history migration preview and confirmation;
- remove HTML and audit downloads from the primary Company Workbench path;
- verify the complete desktop and phone workflow with no generated files.

### Later external stage — Hosted private adapter

Only after an exact environment is approved, implement a hosted adapter with
real authentication, server-side workspace authorization, durable append-only
audit events, encryption, retention/deletion, monitoring, backup, recovery,
rollback, incident response, and named operating ownership. Direct environment
evidence is required; passing local adapter tests is not hosted proof.

## Testing Strategy

Implementation is test-first. Focused tests must prove:

1. route render, filter, recalculation, validation, preview, and HTML display are
   byte-for-byte no-write operations;
2. all four Personal Research routes render truthful states without legacy
   generated outputs;
3. missing canonical inputs fail closed and link to in-app Data Health;
4. report and scenario cache identities invalidate on every relevant source or
   method change;
5. SQLite is not created before an explicit confirmed save;
6. a valid confirmation appends exactly one record and reloads the exact digest;
7. stale, duplicate, invalid, cross-workspace, and pre-commit failure saves
   write nothing; an uncertain commit returns `save_pending_reload`, and no
   failure path falls back to CSV or permits a blind duplicate retry;
8. append-only and supersession rules survive restart and concurrent attempts;
9. legacy import is preview-only until confirmation, transactional, idempotent,
   and fail closed on malformed data;
10. normal Company Workbench exposes no HTML or audit-data download;
11. optional Advanced export remains user-initiated, pathless, and
    repository-no-write; and
12. no calculation, record, migration, or storage state promotes readiness,
    probability, recommendation, or trusted evidence.

After every implementation slice, run focused tests followed by the full
repository suite and the applicable dashboard, Research render, accessibility,
public-wording, public, pilot-readiness, diff-hygiene, whitespace, and staged
hygiene gates. Do not use readiness rebuilds, broad refreshes, pipeline/report
writers, screenshot writers, timing writers, or other generated-artifact
commands as validation for this work.

Protected generated and canonical paths must have identical hashes before and
after each slice. Stage exact intentional code, tests, and documentation only;
never use `git add -A`.

## Acceptance Criteria

The local A+C foundation is complete only when direct current-head evidence
proves all of the following:

- ordinary non-save use of the four-route Personal Research workflow creates or
  changes no repository or app-data file;
- the local database is created only by an explicit confirmed save or confirmed
  legacy import;
- all subsequently confirmed research records persist across application
  restarts and are reloaded with matching identities and digests;
- ordinary research users never need to locate, edit, or open CSV, JSON, HTML,
  report, or database files;
- missing or malformed data remains visibly empty, partial, stale, excluded, or
  withheld without fabrication;
- cache and scenario state cannot cross a profile, provider, source snapshot,
  model version, ticker, or workspace boundary;
- the primary Company Workbench has no download dependency;
- generated-artifact and canonical-source hashes remain unchanged through the
  complete automated and browser workflow matrix;
- all research-only, provenance, rights, Q4, EPS-basis, candidate-context,
  nowcast, calibration, and no-investment-advice boundaries remain enforced;
  and
- the documentation calls this a local single-user storage improvement, not a
  hosted, authenticated, commercially operated, market-validated, or
  calibration-complete product.

## Documentation And Release Boundary

Each verified implementation slice updates ROADMAP, the relevant public and
internal product documentation, the continuation prompt, and draft PR #113 with
the exact behavior and evidence. Public wording should change from `CSV-first`
only after the primary workflow is genuinely app-managed and the regression
matrix proves that normal operation no longer depends on generated outputs.

Keep PR #113 open and draft. Do not merge or deploy publicly without explicit
approval. Do not claim the overall Commercial Research Beta complete while
source, hosted, reviewer, accessibility, calibration, market-validation, or
operating gates remain unproved.
