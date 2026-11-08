"""Bounded note writes remain readable and bind confirmation to the same limit."""
import csv
from dataclasses import replace

import pytest

from src.research_record_authoring import (
    AuthoringPaths, build_authoring_draft, confirm_authoring_preview, preview_authoring_record,
)
from src.research_thesis_journal import JournalEntry, append_journal_entry, load_journal_entries


def paths_at(root, *, max_bytes=None):
    return AuthoringPaths(root/'journal.csv', root/'catalysts.csv', root/'outcomes.csv', max_bytes=max_bytes)


def thesis(summary='A user-authored thesis.', *, supersedes=''):
    return build_authoring_draft('thesis', profile_key='demo', ticker='FICT', fields={
        'thesis_id':'thesis-one', 'summary':summary, 'effective_at':'2026-11-07T11:00:00Z',
        'reviewer':'Synthetic reviewer', 'confidence':'0.50', 'review_due_date':'2026-12-01',
        'supersedes_entry_id':supersedes,
    })


def preview(draft, paths):
    return preview_authoring_record(draft, paths=paths,
        previewed_at='2026-11-07T12:00:00Z', generated_id='entry-new')


def confirm(value, draft, paths):
    return confirm_authoring_preview(value, current_draft=draft, paths=paths,
        active_profile_key='demo', active_ticker='FICT', active_kind=draft.record_kind,
        confirm_reviewed=True)


def existing_entry():
    return JournalEntry('research-thesis-journal-v1', 'entry-one', 'demo', 'FICT',
        'thesis-one', 'thesis', '2026-11-07T10:00:00Z', '2026-11-07T09:00:00Z',
        'Synthetic reviewer', 'The initial thesis.', '', '', '', '', '0.50', '2026-12-01', '')


def test_bounded_preview_rejects_a_field_that_the_csv_reader_cannot_reload(tmp_path):
    draft=thesis('x'*(csv.field_size_limit()+1))
    value=preview(draft,paths_at(tmp_path,max_bytes=2*1024*1024))
    assert value.state=='rejected' and 'field size limit' in value.reason
    assert not value.receipt and not list(tmp_path.iterdir())
    # The opt-in limit leaves legacy authoring behavior unchanged.
    assert preview(draft,paths_at(tmp_path)).state=='reviewable'


def test_bounded_preview_counts_csv_escaping_utf8_header_and_line_endings(tmp_path):
    draft=thesis('Café, "quoted"\n第二行')
    expected=(
        'schema_version,entry_id,profile_key,ticker,thesis_id,entry_type,recorded_at,effective_at,'
        'reviewer,summary,evidence_direction,source,source_ref,source_published_at,confidence,'
        'review_due_date,supersedes_entry_id\r\n'
        'research-thesis-journal-v1,entry-new,demo,FICT,thesis-one,thesis,2026-11-07T12:00:00Z,'
        '2026-11-07T11:00:00Z,Synthetic reviewer,"Café, ""quoted""\n第二行",,,,,0.50,2026-12-01,\r\n'
    ).encode('utf-8')
    too_small=paths_at(tmp_path,max_bytes=len(expected)-1)
    value=preview(draft,too_small)
    assert value.state=='rejected' and 'byte limit' in value.reason
    assert not list(tmp_path.iterdir())
    exact=paths_at(tmp_path,max_bytes=len(expected))
    value=preview(draft,exact)
    assert value.state=='reviewable'
    result=confirm(value,draft,exact)
    assert result.state=='saved' and result.write_performed
    assert exact.journal.read_bytes()==expected
    rows=load_journal_entries(exact.journal)
    assert len(rows)==1 and rows[0].summary=='Café, "quoted"\n第二行'


def test_bounded_revision_counts_existing_bytes_without_adding_another_header(tmp_path):
    unbounded=paths_at(tmp_path)
    append_journal_entry(unbounded.journal,existing_entry())
    original=unbounded.journal.read_bytes()
    draft=thesis('A revised "quoted", user thesis.',supersedes='entry-one')
    value=preview(draft,unbounded)
    reference=tmp_path/'reference.csv'
    reference.write_bytes(original)
    append_journal_entry(reference,value.record)
    expected=reference.read_bytes()
    rejected=preview(draft,replace(unbounded,max_bytes=len(expected)-1))
    assert rejected.state=='rejected' and 'byte limit' in rejected.reason
    assert unbounded.journal.read_bytes()==original
    bounded=replace(unbounded,max_bytes=len(expected))
    result=confirm(preview(draft,bounded),draft,bounded)
    assert result.state=='saved'
    assert bounded.journal.read_bytes()==expected
    assert len(load_journal_entries(bounded.journal))==2


def test_bounded_preview_rejects_existing_oversize_before_parsing_it(tmp_path):
    paths=paths_at(tmp_path,max_bytes=10)
    paths.journal.write_bytes(b'not valid CSV'*10)
    original=paths.journal.read_bytes()
    value=preview(thesis(),paths)
    assert value.state=='rejected' and 'byte limit' in value.reason
    assert paths.journal.read_bytes()==original


@pytest.mark.parametrize('before_limit,after_limit',[(10000,12000),(10000,None),(None,10000)])
def test_confirmation_cannot_change_the_previewed_limit(tmp_path,before_limit,after_limit):
    draft=thesis()
    before=paths_at(tmp_path,max_bytes=before_limit)
    value=preview(draft,before)
    assert value.state=='reviewable'
    result=confirm(value,draft,replace(before,max_bytes=after_limit))
    assert result.state=='preview_stale' and not result.write_performed
    assert not list(tmp_path.iterdir())


def test_concurrent_ledger_growth_stays_stale_and_does_not_append(tmp_path):
    paths=paths_at(tmp_path,max_bytes=10000)
    first=existing_entry()
    append_journal_entry(paths.journal,first)
    draft=thesis('A user revision.',supersedes='entry-one')
    value=preview(draft,paths)
    assert value.state=='reviewable'
    evidence=replace(first,entry_id='evidence-other',entry_type='evidence',
        recorded_at='2026-11-07T11:30:00Z',summary='A concurrent user observation.',
        evidence_direction='supporting',source='company_ir',source_ref='https://example.invalid/source',
        source_published_at='2026-11-07T09:00:00Z',confidence='',review_due_date='')
    append_journal_entry(paths.journal,evidence)
    original=paths.journal.read_bytes()
    result=confirm(value,draft,paths)
    assert result.state=='preview_stale' and not result.write_performed
    assert paths.journal.read_bytes()==original
    assert len(load_journal_entries(paths.journal))==2
