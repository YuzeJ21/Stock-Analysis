"""Read-only summaries of declared independent feedback, not pilot approval.

No free text or participant/session identifiers leave this module's summary.
Provenance comes from operator declarations, not independent human attestation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, time, timedelta, timezone
import io
import json
import math
from pathlib import Path
import re
from statistics import median
import sys


_MAX_BYTES = 2 * 1024 * 1024
_MAX_ROWS = 2000
_SCORES = {
    'task_success': ('completed', 'completed_with_help', 'not_completed'),
    'moderator_help_required': ('none', 'one_prompt', 'multiple_prompts'),
    'readiness_comprehension': ('correct', 'partial', 'incorrect'),
    'evidence_trace_result': ('completed', 'completed_with_help', 'not_completed'),
    'authoring_friction': ('none', 'low', 'medium', 'high'),
    'misuse_risk': ('none', 'uncertain', 'mistook_as_recommendation_or_live_terminal'),
    'trust_in_evidence': ('high', 'medium', 'low'),
    'perceived_performance': ('responsive', 'noticeably_slow', 'appeared_frozen'),
    'repeat_use_intent': ('yes', 'maybe', 'no'),
    'reviewer_signal': ('clear', 'confused', 'blocked_by_environment', 'suggestion_only'),
    'closeout_outcome': ('clear', 'reproducible_ui_issue', 'documentation_gap',
        'environment_limited', 'intentionally_deferred'),
}
_PROVENANCE = ('review_label', 'reviewer_label', 'session_kind', 'delivery_kind',
    'research_revision', 'session_phase')
_REQUIRED = frozenset((*_PROVENANCE, *_SCORES, 'started_at', 'consent_confirmed',
    'consent_withdrawn', 'retention_delete_after', 'time_to_first_answer_minutes'))
_KINDS = {'independent_researcher', 'owner_led', 'automated', 'fixture', 'screenshot'}
_DELIVERIES = {'fictional_demo', 'local_research', 'hosted_private_pilot'}
_ERROR = 'Pilot feedback input is unavailable or invalid.'
_BOUNDARY = ('Operator-declared feedback only; human independence is not verified. '
    'Fictional demos, local research and hosted sessions are separate cohorts. '
    'Intent is not observed return use. These counts do not establish data rights, '
    'hosted operation, investment validity or commercial readiness.')


def _read_rows(path: Path) -> list[dict[str, str]]:
    try:
        if not path.is_file():
            raise ValueError(_ERROR)
        with path.open('rb') as handle:
            raw = handle.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES or b'\x00' in raw:
            raise ValueError(_ERROR)
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
        headers = reader.fieldnames or []
        if (not _REQUIRED <= set(headers) or len(headers) != len(set(headers))
                or len(headers) > 128 or any(not name.strip() for name in headers)):
            raise ValueError(_ERROR)
        rows = []
        for row in reader:
            if len(rows) >= _MAX_ROWS or None in row or any(v is None for v in row.values()):
                raise ValueError(_ERROR)
            rows.append({key: row[key].strip() for key in _REQUIRED})
        return rows
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        raise ValueError(_ERROR) from exc


def _date(value: str) -> date:
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError(_ERROR)
    return result


def _started_at(value: str) -> tuple[datetime, datetime]:
    if len(value) == 10:
        start = datetime.combine(_date(value), time(), tzinfo=timezone.utc)
        return start, start + timedelta(days=1)
    if not 11 <= len(value) <= 40:
        raise ValueError(_ERROR)
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(_ERROR)
    instant = result.astimezone(timezone.utc)
    return instant, instant


def _precedes(before: tuple[datetime, datetime], after: tuple[datetime, datetime]) -> bool:
    # A date denotes an entire day; a timestamp denotes an instant. Preserve
    # that uncertainty rather than manufacture an ordering at midnight.
    return before[0] < after[0] and before[1] <= after[0]


def _exclusion(row: dict[str, str], as_of: date, duplicates: set[str]) -> tuple[str | None, tuple[datetime, datetime] | None]:
    if row['consent_confirmed'] != 'yes':
        return 'no_consent', None
    if row['consent_withdrawn'] == 'yes':
        return 'withdrawn', None
    if row['consent_withdrawn'] != 'no':
        return 'unconfirmed_withdrawal_status', None
    try:
        started = _started_at(row['started_at'])
        expiry = _date(row['retention_delete_after'])
        if expiry < started[0].date():
            raise ValueError(_ERROR)
    except (ValueError, OverflowError):
        return 'invalid_dates', None
    if expiry <= as_of:
        return 'retention_expired', None
    if started[0].date() > as_of:
        return 'future_session', None
    if (any(re.fullmatch(r'[A-Z][0-9]{2,5}', row[key]) is None
            for key in ('review_label', 'reviewer_label'))
            or re.fullmatch('[0-9a-f]{40}', row['research_revision']) is None
            or row['session_kind'] not in _KINDS or row['delivery_kind'] not in _DELIVERIES
            or row['session_phase'] not in {'initial', 'return'}):
        return 'invalid_provenance', None
    if row['review_label'] in duplicates:
        return 'duplicate_session_id', None
    if row['session_kind'] != 'independent_researcher':
        return 'non_independent', None
    return None, started


def _minutes(value: str) -> float | None:
    try:
        number = float(value) if len(value) <= 32 else math.nan
        return number if math.isfinite(number) and 0 <= number <= 1440 else None
    except ValueError:
        return None


def _cohort_summary(revision: str, delivery: str, initials: list[dict[str, str]],
        returns: list[dict[str, str]], ambiguous_initials: int) -> dict:
    scores = {}
    for field, allowed in _SCORES.items():
        counts = Counter(row[field] if row[field] in allowed else 'missing_or_invalid' for row in initials)
        scores[field] = {value: counts[value] for value in (*allowed, 'missing_or_invalid')}
    timings = [value for row in initials if (value := _minutes(row['time_to_first_answer_minutes'])) is not None]
    return {
        'research_revision': revision,
        'delivery_kind': delivery,
        'initial_sessions': len(initials),
        'ambiguous_initial_reviewers': ambiguous_initials,
        'return_sessions': len(returns),
        'returning_reviewers': len({row['reviewer_label'] for row in returns
            if row['task_success'] in {'completed', 'completed_with_help'}}),
        'unassisted_task_completions': sum(row['task_success'] == 'completed'
            and row['moderator_help_required'] == 'none' for row in initials),
        'scores': scores,
        'first_answer': {'answered_sessions': len(timings),
            'median_minutes': float(median(timings)) if timings else None},
    }


def summarize_pilot_feedback(path: Path, *, as_of: date) -> dict:
    """Summarize declared sessions at a fixed cutoff without writes or requests."""
    if type(as_of) is not date:
        raise ValueError(_ERROR)
    rows = _read_rows(Path(path))
    ids = Counter(row['review_label'] for row in rows)
    duplicates = {label for label, count in ids.items() if count > 1}
    excluded = Counter()
    groups = defaultdict(list)
    for row in rows:
        reason, started = _exclusion(row, as_of, duplicates)
        if reason:
            excluded[reason] += 1
        else:
            groups[(row['research_revision'], row['delivery_kind'])].append((started, row))
    cohorts = []
    for (revision, delivery), sessions in sorted(groups.items()):
        initial = {}
        attempts = defaultdict(list)
        for bounds, row in sessions:
            if row['session_phase'] == 'initial':
                attempts[row['reviewer_label']].append((bounds, row))
        ambiguous = 0
        for reviewer, entries in attempts.items():
            entries.sort(key=lambda item: item[0])
            bounds, row = entries[0]
            overlap = [entry for entry in entries if not _precedes(bounds, entry[0])]
            excluded['repeated_initial'] += len(entries) - 1
            if len(overlap) > 1:
                ambiguous += 1
                # One reviewer remains in the denominator, with no guessed
                # outcome/timing. Retain a conservative window for return use.
                bounds = (bounds[0], max(entry[0][1] for entry in overlap))
                row = dict.fromkeys(_REQUIRED, '') | {'reviewer_label': reviewer}
            initial[reviewer] = (bounds, row)
        returns = []
        for started, row in sessions:
            if row['session_phase'] != 'return':
                continue
            baseline = initial.get(row['reviewer_label'])
            if baseline is None or not _precedes(baseline[0], started):
                excluded['unmatched_return'] += 1
            else:
                returns.append(row)
        if initial:
            cohorts.append(_cohort_summary(revision, delivery,
                [value[1] for value in initial.values()], returns, ambiguous))
    return {
        'schema_version': 'pilot-feedback-summary-v1',
        'as_of': as_of.isoformat(),
        'status': 'reported_feedback_available' if cohorts else 'awaiting_external_review',
        'input_sessions': len(rows),
        'excluded_sessions': {key: value for key, value in sorted(excluded.items()) if value},
        'cohorts': cohorts,
        'operated_pilot_ready': False,
        'boundary': _BOUNDARY,
    }


def render_pilot_feedback(summary: dict) -> str:
    """Render only validated aggregate categories; do not pass raw rows here."""
    lines = ['Pilot Feedback Summary', 'Read-only; no input rows are changed or published.',
        f"status: {summary['status']}", f"as_of: {summary['as_of']}",
        f"input_sessions: {summary['input_sessions']}"]
    lines.extend(f'excluded {reason}: {count}' for reason, count in summary['excluded_sessions'].items())
    for cohort in summary['cohorts']:
        lines.append(f"cohort: {cohort['delivery_kind']} @ {cohort['research_revision']}")
        for key in ('initial_sessions', 'ambiguous_initial_reviewers', 'return_sessions',
                'returning_reviewers', 'unassisted_task_completions'):
            lines.append(f"  {key}: {cohort[key]}")
        timing = cohort['first_answer']
        lines.append(f"  first_answer: {timing['answered_sessions']} timed; median_minutes={timing['median_minutes']}")
        lines.extend(f"  {field}: " + ', '.join(f'{value}={count}' for value, count in values.items())
            for field, values in cohort['scores'].items())
    lines.extend(['operated_pilot_ready: false', summary['boundary']])
    return '\n'.join(lines)


class _PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, _ERROR + '\n')


def main(argv: list[str] | None = None) -> int:
    parser = _PrivateArgumentParser(description='Summarize declared pilot sessions without modifying the log.')
    parser.add_argument('--input', required=True)
    parser.add_argument('--as-of', required=True, help='Explicit ISO cutoff date (YYYY-MM-DD)')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = summarize_pilot_feedback(Path(args.input), as_of=_date(args.as_of))
    except (ValueError, OSError):
        print(_ERROR, file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, allow_nan=False) if args.json else render_pilot_feedback(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
