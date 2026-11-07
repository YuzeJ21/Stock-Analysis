"""Observable five-section contract; legacy one-pager integrity remains separate."""
from copy import deepcopy
import pytest
from src.research_accessibility_browser_gate import evaluate_integrated_company_workbench


def observation():
    return dict(brief_count=1,brief_visible=True,display_title='NVDA Company Brief',h1_count=1,
        sections=['Overview','Financial Trends','Valuation & Peers','Research Notes','Data Sources'],
        section_visible=[True]*5,section_heights=[44]*5,selected=['Overview'],
        body_headings=['Overview'],update_count=1,update_visible=True,update_height=44,
        scope_text='Online observations and saved models have separate eligibility.',
        legacy_module_count=0)


def test_one_visible_overview_and_five_usable_sections():
    assert evaluate_integrated_company_workbench(observation())['passed'] is True


@pytest.mark.parametrize('change',[
    {'brief_count':2},{'brief_visible':False},{'display_title':'AMD Company Brief'},
    {'h1_count':2},{'sections':['Overview']},{'section_visible':[True]*4+[False]},
    {'section_heights':[44]*4+[40]},{'selected':['Overview','Valuation & Peers']},
    {'body_headings':['Overview','Research Notes']},{'update_count':0},{'update_visible':False},
    {'update_height':40},{'scope_text':'ready'},{'legacy_module_count':1},
])
def test_each_visible_journey_requirement_fails_closed(change):
    row=deepcopy(observation());row.update(change)
    assert evaluate_integrated_company_workbench(row)['passed'] is False
