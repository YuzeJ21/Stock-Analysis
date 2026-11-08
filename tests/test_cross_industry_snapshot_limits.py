"""Valid historical research must replay exactly or explicitly hit the private size bound."""
from copy import deepcopy

import pytest

from src.online_research_context_store import (
    save_research_context, load_research_context, compare_research_contexts,
)
from test_online_research_context_store import context, SCOPE


def _historical_context(report_count):
    reports=[]
    for index in range(report_count):
        accession=f'0000001234-25-{index:06d}'
        reports.append(dict(accession=accession,form='6-K',period_end=None,report_date='2025-06-30',
            filed='2025-08-01',accepted_at='2025-08-01T12:00:00Z',primary_document=f'event-{index}.htm',
            source_url=f'https://www.sec.gov/Archives/edgar/data/1234/{accession.replace("-", "")}/event-{index}.htm',
            amendment=False))
    triggers=[dict(trigger_type='current_report_filing',anchor=report) for report in reports]
    value=context(scenario=None,notes=None,
        filing_inventory=dict(earnings_reports=reports,review_triggers=triggers),
        filing_coverage=dict(current={'annual':dict(status='facts_pending',reason='new_filing_structured_facts_pending'),
            'interim':dict(status='withheld',reason='newer_reporting_period_known')}),
        scenario_base=dict(status='withheld',reason='validated_current_annual_revenue_required',revenue=None),
        business_trend=dict(periods=[dict(kind='interim',period_start='2021-01-01',period_end='2021-06-30',
            status='available',current=False,currency='TWD',fields={'revenue':dict(value=100,unit='TWD')})],
            metrics=[]),forward_view=dict(review_triggers=triggers),
        gaps=['Latest annual facts are pending; the interim observation remains dated history.'])
    return value


def test_legitimate_dated_native_history_replays_exactly_with_current_model_holds(tmp_path):
    value=_historical_context(100); before=deepcopy(value)
    saved=save_research_context(value,**SCOPE,project_root=tmp_path)
    reopened=load_research_context(saved['snapshot_id'],**SCOPE,project_root=tmp_path)
    assert reopened['context']==before and value==before
    assert compare_research_contexts(value,reopened)['status']=='unchanged'
    assert reopened['historical'] is True and reopened['current'] is False
    assert reopened['context']['filing_coverage']['current']['annual']['status']=='facts_pending'
    assert reopened['context']['scenario_base']['status']=='withheld'
    assert reopened['context']['business_trend']['periods'][0]['current'] is False


def test_legitimate_large_event_catalog_is_explicitly_size_held_without_truncation_or_write(tmp_path):
    value=_historical_context(650); before=deepcopy(value)
    with pytest.raises(ValueError,match='Research snapshot size limit exceeded'):
        save_research_context(value,**SCOPE,project_root=tmp_path)
    assert value==before
    assert list(tmp_path.iterdir())==[]
