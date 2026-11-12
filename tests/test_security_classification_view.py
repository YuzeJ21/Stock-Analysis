import pytest
from test_security_classification import packet,fixture_fetch,OBSERVED
from test_sec_html_bank import extract


def test_listing_counts_are_source_labels_and_unknowns_remain_inspectable():
 from src.security_classification_view import classification_html
 h=classification_html(packet())
 assert 'Security types' in h and 'Preferred' in h and 'Unknown' in h and 'SHA-256' in h
 assert 'directory description' in h and 'financial eligibility' in h and '2026-10-30' in h


def test_listing_gap_filters_keep_the_snapshot_denominator_and_use_distinct_populations():
 from src.security_classification_view import classification_html

 snapshot = packet()
 sec_only = classification_html(snapshot, observation_scope='SEC-only')
 unresolved = classification_html(snapshot, observation_scope='Unresolved directory types')
 assert '6 listing records' in sec_only and '6 listing records' in unresolved
 assert '1 SEC-only' in sec_only and '2 unresolved directory types' in sec_only
 assert 'Matching listing observations (1)' in sec_only and '<strong>TEX</strong>' in sec_only
 assert 'Matching listing observations (2)' in unresolved and '<strong>TEX</strong>' not in unresolved
 assert '<strong>BANK</strong>' in unresolved and '<strong>UNMAP</strong>' in unresolved
 assert '<strong>FICT</strong>' not in unresolved and '<strong>FICT.B</strong>' not in unresolved
 assert 'Matching listing observations (0)' in classification_html(snapshot, 'FICT', observation_scope='SEC-only')


def test_selected_company_profile_and_instrument_stay_independent():
 from src.security_classification import get_company_security_context
 from src.security_classification_view import company_security_html
 c=get_company_security_context('FICT',{},refresh_requested=True,user_agent='Synthetic',fetcher=fixture_fetch([]),observed_at=OBSERVED)
 h=company_security_html(c,'FICT');assert 'Common / ordinary shares' in h and 'domestic annual reporting' in h
 assert '0000001234' in h and '3571' in h and 'domicile' in h
 assert 'Fictional - Preferred Stock' not in h
 assert '<article' not in company_security_html(c,'OTHER')


def test_non_personal_mode_cannot_render_classifications_or_bank_amounts(monkeypatch):
 from src.security_classification_view import classification_html
 from src.sec_exact_filing_view import filing_preview_html
 p=packet();bank=extract();monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
 assert '<section' not in classification_html(p)
 assert '120,000' not in filing_preview_html(bank,'IBN','annual')


def test_bank_view_retains_definition_basis_source_position_and_signed_cashflow():
 from src.sec_exact_filing_view import filing_preview_html
 h=filing_preview_html(extract(),'IBN','annual')
 assert 'Indian GAAP' in h and 'INR' in h and '2026-03-31' in h and '2024-03-31' in h
 assert 'Total income · before interest expense' in h and '-4,000' in h and 'table ' in h and '#f_004' in h
 assert 'Generic revenue' in h and 'withheld' in h.lower()


def test_listing_cache_is_explicit_without_rerender_fetch(monkeypatch):
 from src.security_classification_view import get_listing_classification
 calls=[];state={};f=fixture_fetch(calls)
 assert get_listing_classification(state,refresh_requested=False,user_agent='Synthetic',fetcher=f)['status']=='not_requested'
 assert not calls
 assert get_listing_classification(state,refresh_requested=True,user_agent='Synthetic',fetcher=f,observed_at=OBSERVED)['status']=='inspection_only'
 n=len(calls);assert get_listing_classification(state,refresh_requested=False,user_agent='Synthetic')['status']=='inspection_only';assert len(calls)==n
