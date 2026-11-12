from src.nasdaq_texas_reconciliation import (
    EQUITY_COVERS,
    FUND_COHORTS,
    nasdaq_texas_detail_markdown,
    nasdaq_texas_review_markdown,
)


def test_nasdaq_texas_distinguishes_conversion_execution_and_listing_scope():
    review = nasdaq_texas_review_markdown()

    assert '2026-02-13' in review and 'Nasdaq BX' in review
    assert '2026-03-05' in review and '34-104907' in review
    assert 'September 2026' in review and 'matched volume' in review
    assert 'TXSE and NYSE Texas' in review
    assert '40 securities' in review and 'Full current roster remains unverified' in review
    assert '12 stock classes' in review and '28 ETF identities' in review
    assert 'Historical continuity and individual first executions also remain open' in review
    assert 'Q2 2027' in review and 'primary-listing target' in review


def test_nasdaq_texas_counts_distinct_classes_and_certified_funds():
    assert {record.symbol for record in EQUITY_COVERS} == {
        'ACDC', 'APA', 'CSTL', 'HBAN', 'JBHT', 'NDAQ', 'NUTX', 'RMIX', 'ROAD', 'RUSHA', 'RUSHB', 'SPCX',
    }
    assert [len(group.members) for group in FUND_COHORTS] == [25, 3]
    assert len({symbol for group in FUND_COHORTS for symbol, _ in group.members}) == 28
    assert 'RUSHA** · Class A common stock' in nasdaq_texas_detail_markdown()
    assert 'RUSHB** · Class B common stock' in nasdaq_texas_detail_markdown()


def test_etf_certification_and_effective_dates_are_separate_from_stock_admissions():
    detail = nasdaq_texas_detail_markdown()

    assert '2026-10-26' in detail and '2026-10-27' in detail
    assert '2026-10-30' in detail and '2026-11-02' in detail
    assert 'BWIN' in detail and 'CSTL' in detail and 'NUTX' in detail
    assert 'Admission remains open' in detail
    assert '26000457.pdf' in detail


def test_q3_covers_confirm_dual_registration_as_filed_with_bwin_still_open():
    review = nasdaq_texas_review_markdown()
    detail = nasdaq_texas_detail_markdown()

    assert '2 of 3 independently confirmed' in review
    assert 'BWIN admission remains open' in review
    assert 'archives reviewed through 2026-11-04' in detail
    _, candidates = detail.split('- **BWIN**', 1)
    bwin, candidates = candidates.split('- **CSTL**', 1)
    cstl, candidates = candidates.split('- **NUTX**', 1)
    nutx, _ = candidates.split('**Current roster**', 1)
    assert '2026-05-11' in bwin and '2026-10-27' in bwin
    assert 'November 9 Form 10-Q' in bwin and 'only Nasdaq Global Select Market' in bwin
    assert 'Rechecked 2026-11-12' in bwin
    assert '000178175526000068/bwin-20260930.htm' in bwin
    assert 'admission remains open' in bwin.lower()
    assert 'Admission remains open' in bwin
    assert 'Planned 2026-08-17 in Form 8-A' in cstl
    assert 'linkedin.com/' not in cstl
    assert '2026-09-23' in nutx
    assert all('Form 8-A' in row and 'exchange certification' in row for row in (bwin, cstl, nutx))

    cstl_cover = 'https://www.sec.gov/Archives/edgar/data/1447362/000162828026071038/cstl-20260930.htm'
    nutx_cover = 'https://www.sec.gov/Archives/edgar/data/1479681/000162828026070993/nutx-20260930.htm'
    assert f'[Form 10-Q filed 2026-11-05]({cstl_cover})' in cstl
    assert 'The Nasdaq Global Market' in cstl
    assert f'[Form 10-Q filed 2026-11-05]({nutx_cover})' in nutx
    assert 'The Nasdaq Stock Market LLC' in nutx
    assert all('period ended 2026-09-30' in row and 'Nasdaq Texas, LLC' in row for row in (cstl, nutx))
    assert 'Historical start dates remain unverified' in detail

    equity = detail.split('**Common stock · Dual registration as filed**', 1)[1].split('**Victory Portfolios II', 1)[0]
    assert f'**CSTL** · Common stock · [10-Q, 2026-11-05]({cstl_cover})' in equity
    assert f'**NUTX** · Common stock · [10-Q, 2026-11-05]({nutx_cover})' in equity
    assert '**BWIN**' not in equity


def test_public_directory_presence_does_not_establish_nasdaq_texas_roster_membership():
    detail = nasdaq_texas_detail_markdown()

    assert 'SymbolDirDefs' in detail
    assert 'no Nasdaq Texas dual-listing field' in detail
    assert 'trading-system changes' in detail
    assert 'archiveheadlines' in detail


def test_discover_places_dated_nasdaq_texas_evidence_inside_us_listings(monkeypatch):
    from src import dashboard
    from src import online_peer_coverage_ui, self_service_research_coverage_ui

    stack = []
    rendered = []

    class Scope:
        def __init__(self, label):
            self.label = label

        def __enter__(self):
            stack.append(self.label)
            return self

        def __exit__(self, *_):
            stack.pop()

    class StreamlitStub:
        session_state = {}

        def expander(self, label, **_):
            return Scope(label)

        def tabs(self, labels):
            return [Scope(label) for label in labels]

        def spinner(self, label):
            return Scope(label)

        def button(self, *_args, **_kwargs):
            return False

        def checkbox(self, label, **_):
            rendered.append((tuple(stack), label))
            return label == 'Show Nasdaq Texas security evidence'

        def markdown(self, value, **_):
            rendered.append((tuple(stack), value))

    monkeypatch.setattr(dashboard, 'st', StreamlitStub())
    monkeypatch.setattr(online_peer_coverage_ui, 'render_peer_coverage', lambda *_a, **_k: None)
    monkeypatch.setattr(self_service_research_coverage_ui, 'render_self_service_coverage', lambda *_a: None)
    monkeypatch.setattr(dashboard, 'handle_coverage_checkpoint_action', lambda *_a, **_k: {'status': 'idle'})
    monkeypatch.setattr(dashboard, 'get_online_us_universe', lambda *_a, **_k: {'status': 'unavailable'})
    monkeypatch.setattr(dashboard, 'universe_coverage_html', lambda *_a: '')
    monkeypatch.setattr(dashboard, 'get_listing_classification', lambda *_a, **_k: {'status': 'unavailable'})
    monkeypatch.setattr(dashboard, 'classification_html', lambda *_a: '')
    monkeypatch.setattr(dashboard, 'get_online_coverage_study', lambda *_a, **_k: {'status': 'unavailable'})
    monkeypatch.setattr(dashboard, 'coverage_study_html', lambda *_a: '')

    dashboard.render_online_coverage_study()

    path = ('Coverage studies', 'U.S. listings', 'Nasdaq Texas (NTX) listing check')
    assert (path, 'Show Nasdaq Texas security evidence') in rendered
    assert any(scope == path and 'BWIN admission remains open' in content for scope, content in rendered)
    assert any(scope == path and 'November 9 Form 10-Q' in content for scope, content in rendered)
