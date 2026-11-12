"""Dated, read-only review of GIX registration, opening and listings."""

SEC_ORDER = 'https://www.sec.gov/files/rules/other/2025/34-102853.pdf'
SEC_TRADING_NOTICE = 'https://www.sec.gov/files/rules/sro/gix/2026/34-105650.pdf'
SEC_EXHIBIT_N = 'https://www.sec.gov/files/rules/other/2024/exhibit-n-green-impact-exchange-llc.pdf'
GIX_HOME = 'https://www.tradegix.com/'
GIX_RELEASE = GIX_HOME + 'news/gix-appoints-sara-dillon-as-chief-technology-officer'
EDGAR_SEARCH = (
    'https://efts.sec.gov/LATEST/search-index?q=%22Green+Impact+Exchange%22'
    '&dateRange=custom&startdt=2025-04-11&enddt=2026-11-12'
    '&forms=8-A12B%2C8-A12B%2FA%2CCERT%2CCERT%2FA%2C25%2C25-NSE%2C25%2FA%2C25-NSE%2FA'
)


def gix_review_markdown() -> str:
    return f"""
Reviewed 2026-11-12 · Dated evidence review

- **SEC registration · Confirmed.** The SEC approved Green Impact Exchange, LLC as a national securities exchange on 2025-04-11, subject to conditions before operations could begin. [SEC order 34-102853]({SEC_ORDER})
- **Trading launch · Unverified.** GIX reported it had yet to begin trading as of 2026-05-28. Its 2026-07-01 release targets Q1 2027 for the platform, while its homepage still says H2 2026. The review found no official confirmation that trading began. First trading day remains unknown. [SEC notice 34-105650]({SEC_TRADING_NOTICE}) · [GIX July release]({GIX_RELEASE}) · [GIX homepage]({GIX_HOME})
- **Current listings · Count unknown.** There are 0 security identities verified in this review. The 2024-05-09 Exhibit N reported no traded securities at that time. The current GIX listing page provides application materials. A complete dated roster or a filing or notice tying a specific issuer, ticker and security class to an effective GIX listing is still needed. [SEC Exhibit N]({SEC_EXHIBIT_N}) · [GIX listing page]({GIX_HOME}listing)

The exact exchange-name search returned 0 EDGAR matches in selected registration, certification and removal forms from 2025-04-11 through 2026-11-12. The search can miss alternate names, paper filings or unindexed exhibits. Trading under unlisted trading privileges and a GIX listing require separate evidence. [EDGAR search result]({EDGAR_SEARCH})
"""
