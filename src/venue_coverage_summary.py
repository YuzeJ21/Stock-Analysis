"""Read-only summary of the dated venue evidence in Discover."""

from html import escape

from src.nasdaq_texas_reconciliation import EQUITY_COVERS, FUND_COHORTS
from src.txse_reconciliation import TXSE_IDENTITIES, TXSE_LATER_IDENTITIES


_STYLE = """<style>
.venue-coverage-summary ul { list-style: none; margin: 0; padding: 0; }
.venue-coverage-summary li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.35fr) minmax(0, 1.25fr);
    gap: 0.4rem 1rem;
    padding: 0.8rem 0;
    border-top: 1px solid color-mix(in srgb, currentColor 18%, transparent);
    overflow-wrap: anywhere;
}
.venue-coverage-summary li h4 { font-size: 1rem; padding: 0; margin: 0; }
.venue-coverage-summary li p { margin: 0; }
@media (max-width: 700px) {
    .venue-coverage-summary li { grid-template-columns: minmax(0, 1fr); }
}
</style>"""


def venue_coverage_summary_html() -> str:
    stock_classes = len(EQUITY_COVERS)
    etfs = sum(len(group.members) for group in FUND_COHORTS)
    txse_listings = len(TXSE_IDENTITIES) + len(TXSE_LATER_IDENTITIES)
    # NYSE Texas and LTSE counts describe the completed November 12 filing reviews.
    # Rechecking filings in a session does not rewrite these dated observations.
    reviews = (
        (
            'nasdaq-texas', 'Nasdaq Texas (NTX)', 'Reviewed 2026-11-05 · BWIN rechecked 2026-11-12',
            f'{stock_classes + etfs} securities with dual-listing evidence',
            f'{stock_classes} stock classes and {etfs} ETFs.',
            'BWIN admission, the full current roster, primary listings, first trades and listing continuity remain unverified.',
        ),
        (
            'nyse-texas', 'NYSE Texas', 'Reviewed 2026-11-12',
            '5 of 5 selected securities', 'Dual registration verified as filed.',
            'DIT’s first trade, the full current roster and continuous listing status remain unverified.',
        ),
        (
            'txse', 'Texas Stock Exchange (TXSE)', 'Directory observed 2026-11-12',
            f'{txse_listings} securities in the dated directory',
            '24 primary and 1 secondary. Trading confirmed by July 31.',
            'July 10 as the first execution date, listing continuity and later roster changes remain unverified.',
        ),
        (
            'ltse', 'Long-Term Stock Exchange (LTSE)', 'Reviewed 2026-11-12',
            '3 of 3 selected share classes', 'ASAN, TDUP and BLX verified as filed.',
            'Their current status, the full roster and first trades remain unverified.',
        ),
        (
            'gix', 'Green Impact Exchange (GIX)', 'Reviewed 2026-11-12',
            '0 security identities verified', 'SEC registration confirmed.',
            'Trading start, first trade and the current listing count remain unknown.',
        ),
    )
    rows = ''.join(
        f'<li data-venue="{venue}"><div><h4>{escape(name)}</h4><small>{escape(date)}</small></div>'
        f'<p><strong>{escape(count)}</strong><br>{escape(evidence)}</p><p>{escape(gap)}</p></li>'
        for venue, name, date, count, evidence, gap in reviews
    )
    return (
        _STYLE + '<section class="venue-coverage-summary" aria-label="Dated venue reviews">'
        '<h3>Dated venue reviews</h3>'
        '<p>Counts apply to each dated sample or directory. Full U.S. coverage remains unverified.</p>'
        f'<ul role="list">{rows}</ul></section>'
    )
