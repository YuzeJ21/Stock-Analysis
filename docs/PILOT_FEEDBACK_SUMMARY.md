# Independent feedback summary

The existing pilot log can now produce a read-only, cohort-specific summary.
It is an operator tool for measuring completed research sessions. It does not
collect telemetry, verify human identity, change readiness or approve operation.

## Prepare an external working log

For a **new** review round, create a fresh private directory. This command does
not replace an earlier round's log; keep the printed directory path for later
commands in this shell.

```bash
pilot_feedback_dir=$(mktemp -d "${TMPDIR:-/tmp}/stock-pilot-feedback.XXXXXXXX")
chmod 700 "$pilot_feedback_dir"
cp docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv "$pilot_feedback_dir/feedback.csv"
chmod 600 "$pilot_feedback_dir/feedback.csv"
printf '%s\n' "$pilot_feedback_dir"
```

Delete the example row; it contains choices and placeholders, not real feedback.
Keep the CSV outside Git. Record only anonymous labels and minimal workflow
feedback. Explain participation, withdrawal and the deletion date before use.
The program excludes expired/withdrawn rows from aggregates; it does not delete
them. The operator must execute the existing retention/deletion procedure.

For an existing log, work on a private copy and preserve the original until
the migration is checked. Add provenance only from contemporaneously recorded
facts; never infer independence, revision, delivery mode, phase or participant
linkage from an old row. Leave unknown values blank so they are excluded. The
old 33-column format needs the five new provenance headers before this command
can read it. Do not overwrite an existing log with the template.

Use the [current company research task](PILOT_REVIEW_FEEDBACK_TEMPLATE.md#current-company-research-task).
One input log covers this one named exercise. Keep optional/legacy exercise
results in separate logs, including when migrating older feedback; identical
delivery/revision labels do not make different tasks comparable.
The existing 10–20 independent-reviewer target remains unchanged; a smaller
formative round can identify defects but does not complete that target.

## Provenance columns

| Column | Required value |
| --- | --- |
| `review_label` | Unique anonymous session token, e.g. `S01`. One uppercase letter and 2–5 digits. Duplicate IDs are all excluded. |
| `reviewer_label` | Stable anonymous participant token, e.g. `P01`, with the same token format. No name, address, email or account identifier. |
| `session_kind` | `independent_researcher`, `owner_led`, `automated`, `fixture`, or `screenshot`. Only declared independent researcher sessions enter usage metrics. |
| `delivery_kind` | `fictional_demo`, `local_research`, or `hosted_private_pilot`. These test different capabilities and are never pooled. |
| `research_revision` | Full lowercase 40-character Git commit of the tested code. A new revision starts a separate cohort. |
| `session_phase` | `initial` for a first task attempt, `return` for an actual later visit. |
| `started_at` | `YYYY-MM-DD` or a timezone-aware ISO timestamp. A date-only value represents the entire UTC day, so a visit within that day cannot prove later return use. Timestamps use their UTC date at the cutoff. |
| Consent fields | Exactly `yes` for `consent_confirmed` and `no` for `consent_withdrawn`. Missing/ambiguous answers do not qualify. |
| `retention_delete_after` | ISO date later than the cutoff. A row expires on its deletion date; it cannot precede the session date. |

All provenance is declared by the operator. Labels cannot establish the target
persona, independence, authenticity or truly voluntary consent. Review those
facts separately before treating counts as independent evidence. A declared
hosted session does not establish that hosting controls were verified.

## Run

```bash
make pilot-feedback-summary INPUT="$pilot_feedback_dir/feedback.csv" AS_OF=2026-11-26
make pilot-feedback-summary INPUT="$pilot_feedback_dir/feedback.csv" AS_OF=2026-11-26 JSON=1
python3 -B -m src.pilot_feedback --input "$pilot_feedback_dir/feedback.csv" --as-of 2026-11-26 --json
```

Replace the example cutoff with the actual review date. No provider is contacted.
The input is not modified. The output contains fixed categories, counts and
cohort revisions; it excludes participant/session labels, input paths, notes,
reproduction text, investment opinions and other raw fields. Counts for small
cohorts are not an anonymity guarantee; keep reports private unless separately
reviewed for sharing. Do not commit raw reviewer logs.

## Interpret the result

- `awaiting_external_review`: no qualifying initial sessions. Empty/header-only
  logs and the placeholder template produce no external evidence.
- `reported_feedback_available`: at least one declared initial session exists.
  This is not a pass, maturity score, demand claim or approval.
- Each revision/delivery cohort has its own initial-session denominator. The
  earliest eligible initial attempt per reviewer is used; repeated initial
  rows are counted separately as exclusions. An unsuccessful attempt is never
  dropped because it failed.
- If recorded dates/timestamps cannot establish which initial attempt came
  first, the reviewer still contributes one denominator and an
  `ambiguous_initial_reviewers` count. All initial scores and timing stay
  missing; session labels never decide the result. A return must provably occur
  after the entire possible initial window.
- Every score has a `missing_or_invalid` count. An incomplete scorecard remains
  in the denominator, and no missing answer becomes a success or zero time.
- `unassisted_task_completions` requires both `completed` and `none` for help.
  The separate score distributions retain moderator prompts and other gaps.
- The first-answer median uses only valid finite times from 0 to 1,440 minutes.
  Its answered-session count is separate from the full denominator.
- `return_sessions` includes matching later attempts, even failed ones.
  `returning_reviewers` counts each participant at most once, only when a later
  session in the same cohort has a completed task. Intent is reported separately.
- `excluded_sessions` explains fixed eligibility reasons. Malformed schemas,
  duplicate/missing headers, surplus cells, invalid UTF-8, more than 2,000 rows
  or more than 2 MiB fail with a generic error and exit code 2. Unconsented,
  withdrawn, expired and future rows cannot contribute research-use evidence.

`operated_pilot_ready` stays false. Independent observation, reproducible issue
review, source rights, actual identity/host checks, audit recovery, retention
execution and available operational ownership remain separate gates. A test
fixture's summary proves the software contract only.
