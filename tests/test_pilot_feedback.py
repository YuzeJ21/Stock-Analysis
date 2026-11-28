"""Constructed feedback verifies software, never evidence of actual reviewers."""

import csv
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 11, 26)
REVISION = '709601485c6456275d779c58aedd6fbb55f39f6d'
FIELDS = (
    'review_label', 'reviewer_label', 'session_kind', 'delivery_kind',
    'research_revision', 'session_phase', 'started_at', 'consent_confirmed',
    'consent_withdrawn', 'retention_delete_after', 'task_success',
    'moderator_help_required', 'readiness_comprehension', 'evidence_trace_result',
    'authoring_friction', 'misuse_risk', 'trust_in_evidence',
    'perceived_performance', 'repeat_use_intent', 'reviewer_signal',
    'closeout_outcome', 'time_to_first_answer_minutes', 'notes',
)


def row(label='S01', reviewer='P01', **changes):
    return dict(
        review_label=label, reviewer_label=reviewer,
        session_kind='independent_researcher', delivery_kind='local_research',
        research_revision=REVISION, session_phase='initial',
        started_at='2026-11-24T14:00:00-05:00', consent_confirmed='yes',
        consent_withdrawn='no', retention_delete_after='2026-12-15',
        task_success='completed', moderator_help_required='none',
        readiness_comprehension='correct', evidence_trace_result='completed',
        authoring_friction='low', misuse_risk='none', trust_in_evidence='high',
        perceived_performance='responsive', repeat_use_intent='yes',
        reviewer_signal='clear', closeout_outcome='clear',
        time_to_first_answer_minutes='2', notes='PRIVATE_FEEDBACK_SENTINEL',
    ) | changes


def log(tmp_path, rows, *, fields=FIELDS):
    path = tmp_path / 'PRIVATE_INPUT_PATH.csv'
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def summary(path):
    from src.pilot_feedback import summarize_pilot_feedback
    return summarize_pilot_feedback(path, as_of=AS_OF)


def test_mixed_log_keeps_failed_and_missing_initial_attempts_in_denominator(tmp_path):
    path = log(tmp_path, [
        row(),
        row('S02', 'P02', task_success='not_completed',
            moderator_help_required='multiple_prompts',
            readiness_comprehension='partial', time_to_first_answer_minutes=''),
        row('S03', session_phase='return', started_at='2026-11-25T15:00:00Z'),
        row('S04', 'P04', session_kind='automated'),
        row('S05', 'P05', consent_withdrawn='yes'),
        row('S06', 'P06', research_revision='unverified'),
        row('S07', 'P07', task_success='', time_to_first_answer_minutes='4'),
    ])
    result = summary(path)
    assert result['status'] == 'reported_feedback_available'
    assert result['input_sessions'] == 7
    assert result['excluded_sessions'] == {
        'non_independent': 1, 'withdrawn': 1, 'invalid_provenance': 1,
    }
    cohort, = result['cohorts']
    assert cohort['initial_sessions'] == 3
    assert cohort['return_sessions'] == 1
    assert cohort['returning_reviewers'] == 1
    assert cohort['unassisted_task_completions'] == 1
    assert cohort['scores']['task_success'] == {
        'completed': 1, 'completed_with_help': 0, 'not_completed': 1,
        'missing_or_invalid': 1,
    }
    assert cohort['first_answer'] == {'answered_sessions': 2, 'median_minutes': 3.0}
    serialized = json.dumps(result)
    for value in ('PRIVATE_FEEDBACK_SENTINEL', 'PRIVATE_INPUT_PATH', 'P01', 'S01'):
        assert value not in serialized


@pytest.mark.parametrize(('changes', 'reason'), [
    ({'consent_confirmed': 'no'}, 'no_consent'),
    ({'consent_confirmed': ''}, 'no_consent'),
    ({'consent_withdrawn': ''}, 'unconfirmed_withdrawal_status'),
    ({'consent_withdrawn': 'yes'}, 'withdrawn'),
    ({'retention_delete_after': '2026-11-26'}, 'retention_expired'),
    ({'retention_delete_after': 'not a date'}, 'invalid_dates'),
    ({'started_at': '2026-11-27'}, 'future_session'),
    ({'started_at': '2026-11-24T14:00:00'}, 'invalid_dates'),
    ({'retention_delete_after': '2026-11-23'}, 'invalid_dates'),
    ({'session_kind': 'fixture'}, 'non_independent'),
    ({'session_kind': 'owner_led'}, 'non_independent'),
    ({'session_kind': 'screenshot'}, 'non_independent'),
    ({'session_kind': ''}, 'invalid_provenance'),
    ({'reviewer_label': 'someone@example.com'}, 'invalid_provenance'),
    ({'delivery_kind': 'live'}, 'invalid_provenance'),
    ({'session_phase': 'maybe'}, 'invalid_provenance'),
])
def test_unqualified_rows_cannot_establish_external_evidence(tmp_path, changes, reason):
    result = summary(log(tmp_path, [row(**changes)]))
    assert result['status'] == 'awaiting_external_review'
    assert result['cohorts'] == []
    assert result['excluded_sessions'] == {reason: 1}


def test_duplicate_session_ids_are_all_excluded_even_with_different_content(tmp_path):
    result = summary(log(tmp_path, [row(), row(reviewer='P02', task_success='not_completed')]))
    assert result['excluded_sessions'] == {'duplicate_session_id': 2}
    assert result['cohorts'] == []


def test_first_attempt_is_chronological_not_csv_order_and_intent_is_not_return(tmp_path):
    result = summary(log(tmp_path, [
        row('S02', started_at='2026-11-25', task_success='completed'),
        row('S01', started_at='2026-11-24', task_success='not_completed'),
    ]))
    assert result['excluded_sessions'] == {'repeated_initial': 1}
    cohort, = result['cohorts']
    assert cohort['initial_sessions'] == 1
    assert cohort['scores']['task_success']['not_completed'] == 1
    assert cohort['scores']['repeat_use_intent']['yes'] == 1
    assert cohort['returning_reviewers'] == 0


def test_returns_require_later_completed_visit_in_same_delivery_and_revision(tmp_path):
    result = summary(log(tmp_path, [
        row('S01'),
        row('S02', session_phase='return', started_at='2026-11-23'),
        row('S03', session_phase='return', started_at='2026-11-25', task_success='not_completed'),
        row('S04', session_phase='return', started_at='2026-11-25', delivery_kind='fictional_demo'),
        row('S05', session_phase='return', started_at='2026-11-25', research_revision='a' * 40),
        row('S06', session_phase='return', started_at='2026-11-25'),
        row('S07', session_phase='return', started_at='2026-11-26'),
    ]))
    assert result['excluded_sessions']['unmatched_return'] == 3
    cohort, = result['cohorts']
    assert cohort['return_sessions'] == 3
    assert cohort['returning_reviewers'] == 1
    assert cohort['initial_sessions'] == 1


def test_delivery_modes_and_revisions_are_never_pooled(tmp_path):
    result = summary(log(tmp_path, [
        row('S01'), row('S02', delivery_kind='fictional_demo'),
        row('S03', delivery_kind='hosted_private_pilot'),
        row('S04', research_revision='b' * 40),
    ]))
    assert len(result['cohorts']) == 4
    assert [c['initial_sessions'] for c in result['cohorts']] == [1, 1, 1, 1]
    assert all(c['returning_reviewers'] == 0 for c in result['cohorts'])
    assert result['operated_pilot_ready'] is False


@pytest.mark.parametrize('value', ['', '-1', 'NaN', 'Infinity', '1e999', '1441', '2 minutes'])
def test_missing_and_invalid_timing_never_becomes_zero_or_discards_attempt(tmp_path, value):
    cohort, = summary(log(tmp_path, [row(time_to_first_answer_minutes=value)]))['cohorts']
    assert cohort['initial_sessions'] == 1
    assert cohort['first_answer'] == {'answered_sessions': 0, 'median_minutes': None}


def test_bad_score_is_missing_and_cannot_establish_unassisted_success(tmp_path):
    cohort, = summary(log(tmp_path, [row(moderator_help_required='PRIVATE_BAD_ENUM')]))['cohorts']
    assert cohort['initial_sessions'] == 1
    assert cohort['unassisted_task_completions'] == 0
    assert cohort['scores']['moderator_help_required']['missing_or_invalid'] == 1
    assert 'PRIVATE_BAD_ENUM' not in json.dumps(cohort)


def test_cli_outputs_only_aggregate_counts_without_writing_files_or_contacting_providers(tmp_path):
    path = log(tmp_path, [row()])
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    program = '''
import socket, sys
def deny(*a, **k):
    raise AssertionError('Feedback summary attempted transport')
socket.socket.connect = socket.socket.connect_ex = deny
from src.pilot_feedback import main
raise SystemExit(main(sys.argv[1:]))
'''
    result = subprocess.run([sys.executable, '-B', '-c', program,
        '--input', str(path), '--as-of', AS_OF.isoformat(), '--json'], cwd=tmp_path,
        env={**os.environ, 'PYTHONPATH': str(ROOT)}, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['cohorts'][0]['initial_sessions'] == 1
    for private in ('P01', 'S01', 'PRIVATE_FEEDBACK_SENTINEL', str(path)):
        assert private not in result.stdout + result.stderr
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize('body', [
    'review_label,review_label\nS01,S02\n',
    ',review_label\nS01,S02\n',
    'only_one_header\nS01\n',
    '\xff',
    'x' * (2 * 1024 * 1024 + 1),
], ids=['duplicate-headers', 'blank-header', 'missing-columns', 'invalid-utf8', 'oversized'])
def test_malformed_input_has_generic_error_without_echoing_private_data(tmp_path, body):
    path = tmp_path / 'PRIVATE_PATH.csv'
    path.write_bytes(body.encode('latin-1'))
    result = subprocess.run([sys.executable, '-B', '-m', 'src.pilot_feedback',
        '--input', str(path), '--as-of', AS_OF.isoformat()], cwd=ROOT,
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr == 'Pilot feedback input is unavailable or invalid.\n'


def test_empty_log_has_no_actual_user_evidence(tmp_path):
    result = summary(log(tmp_path, []))
    assert result['status'] == 'awaiting_external_review'
    assert result['input_sessions'] == 0
    assert result['cohorts'] == []
    assert result['operated_pilot_ready'] is False


def test_make_entrypoint_summarizes_without_modifying_input(tmp_path):
    path = log(tmp_path, [row()])
    before = path.read_bytes()
    result = subprocess.run(['make', '--no-print-directory', 'pilot-feedback-summary',
        f'INPUT={path}', 'AS_OF=2026-11-26', 'JSON=1'], cwd=ROOT,
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['cohorts'][0]['initial_sessions'] == 1
    assert path.read_bytes() == before


def test_placeholder_template_cannot_establish_a_real_session():
    result = summary(ROOT / 'docs/PILOT_REVIEW_FEEDBACK_LOG_TEMPLATE.csv')
    assert result['status'] == 'awaiting_external_review'
    assert result['cohorts'] == []


def test_row_bound_and_surplus_cells_fail_closed_without_raw_values(tmp_path):
    path = log(tmp_path, [row() for _ in range(2001)])
    with pytest.raises(ValueError, match='^Pilot feedback input is unavailable or invalid.$'):
        summary(path)
    path = log(tmp_path, [row()])
    path.write_text(path.read_text().rstrip() + ',PRIVATE_SURPLUS\n')
    with pytest.raises(ValueError, match='^Pilot feedback input is unavailable or invalid.$'):
        summary(path)


def test_cutoff_is_required_and_invalid_cutoff_never_prints_the_supplied_value(tmp_path):
    path = log(tmp_path, [])
    result = subprocess.run([sys.executable, '-B', '-m', 'src.pilot_feedback',
        '--input', str(path), '--as-of', 'PRIVATE_BAD_DATE'], cwd=ROOT,
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert result.stderr == 'Pilot feedback input is unavailable or invalid.\n'


@pytest.mark.parametrize(('initial', 'returned', 'expected'), [
    ('2026-11-24', '2026-11-24T09:00:00Z', 0),
    ('2026-11-24T09:00:00Z', '2026-11-24', 0),
    ('2026-11-24', '2026-11-25T00:00:00Z', 1),
    ('2026-11-24T09:00:00Z', '2026-11-24T09:00:00Z', 0),
    ('2026-11-24T09:00:00Z', '2026-11-24T09:00:01Z', 1),
])
def test_return_order_must_be_provable_at_recorded_precision(tmp_path, initial, returned, expected):
    cohort, = summary(log(tmp_path, [
        row(started_at=initial), row('S02', session_phase='return', started_at=returned),
    ]))['cohorts']
    assert cohort['returning_reviewers'] == expected


def test_tied_initial_attempts_keep_one_unknown_outcome_in_denominator(tmp_path):
    cohort, = summary(log(tmp_path, [
        row('S02', started_at='2026-11-24', task_success='not_completed'),
        row('S01', started_at='2026-11-24', task_success='completed'),
    ]))['cohorts']
    assert cohort['initial_sessions'] == 1
    assert cohort['ambiguous_initial_reviewers'] == 1
    assert cohort['scores']['task_success'] == {
        'completed': 0, 'completed_with_help': 0, 'not_completed': 0,
        'missing_or_invalid': 1,
    }
    assert cohort['first_answer']['answered_sessions'] == 0
    assert cohort['unassisted_task_completions'] == 0


def test_make_handles_quotes_dollars_and_backticks_as_literal_filename_data(tmp_path):
    plain = log(tmp_path, [row()])
    path = tmp_path / 'pilot"$(shell touch PRIVATE_MAKE_SENTINEL)`literal`.csv'
    plain.rename(path)
    result = subprocess.run(['make', '-s', '--no-print-directory', '-C', str(ROOT),
        'pilot-feedback-summary', f'INPUT={path}', 'AS_OF=2026-11-26', 'JSON=1'],
        cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['cohorts'][0]['initial_sessions'] == 1
    assert not (ROOT / 'PRIVATE_MAKE_SENTINEL').exists()
    assert not (tmp_path / 'PRIVATE_MAKE_SENTINEL').exists()


@pytest.mark.parametrize('extra', [
    ['PRIVATE_ARGUMENT_SENTINEL'], ['--private-sentinel'], ['--as-of'],
])
def test_argument_errors_do_not_echo_private_tokens(tmp_path, extra):
    path = log(tmp_path, [])
    result = subprocess.run([sys.executable, '-B', '-m', 'src.pilot_feedback',
        '--input', str(path), '--as-of', '2026-11-26', *extra], cwd=ROOT,
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr == 'Pilot feedback input is unavailable or invalid.\n'
