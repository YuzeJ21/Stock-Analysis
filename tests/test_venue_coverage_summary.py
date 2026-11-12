import re


def test_summary_keeps_evidence_counts_and_open_gaps_with_their_venues():
    from src.venue_coverage_summary import venue_coverage_summary_html

    html = venue_coverage_summary_html()
    rows = dict(re.findall(r'<li data-venue="([\w-]+)">(.*?)</li>', html, re.S))
    assert tuple(rows) == ('nasdaq-texas', 'nyse-texas', 'txse', 'ltse', 'gix')
    for venue, fragments in {
        'nasdaq-texas': ('40 securities', '12 stock classes', '28 ETFs', '2026-11-05', 'BWIN admission'),
        'nyse-texas': ('5 of 5 selected securities', 'as filed', 'DIT’s first trade', '2026-11-12'),
        'txse': ('25 securities', '24 primary', '1 secondary', 'July 10', '2026-11-12'),
        'ltse': ('3 of 3 selected share classes', 'as filed', 'ASAN, TDUP and BLX', 'current status', '2026-11-12'),
        'gix': ('0 security identities verified', 'SEC registration confirmed', 'current listing count', '2026-11-12'),
    }.items():
        for fragment in fragments:
            assert fragment in rows[venue]

    assert 'Full U.S. coverage remains unverified.' in html
    assert '73 securities' not in html
