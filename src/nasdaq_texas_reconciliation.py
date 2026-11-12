"""Dated Nasdaq Texas operations and listing evidence for Discover."""

from dataclasses import dataclass

SEC_ARCHIVE = 'https://www.sec.gov/Archives/edgar/data/'
SEC_CONVERSION = 'https://www.sec.gov/Archives/edgar/vprr/2600/26000072.pdf'
SEC_STANDARDS = 'https://www.sec.gov/files/rules/sro/bx/2026/34-104907.pdf'
SEC_PRIMARY_TARGET = 'https://www.sec.gov/files/rules/sro/nasdaqtx/2026/34-106520.pdf'
SEC_OCTOBER_FORM_1 = 'https://www.sec.gov/Archives/edgar/vprr/2600/26000457.pdf'
NASDAQ_LAUNCH = 'https://ir.nasdaq.com/news-releases/news-release-details/nasdaq-texas-launches-inaugural-dual-listings'
NASDAQ_VOLUME = 'https://classic.nasdaqtrader.com/trader.aspx?id=marketshare'
NASDAQ_VICTORY_NOTICE = 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ETP2026-175'
NASDAQ_ARCHIVE = 'https://www.nasdaqtrader.com/Trader.aspx?id=archiveheadlines&cat_id='
NASDAQ_SYMBOL_DEFINITIONS = 'https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs'
REVIEW_DATE = '2026-11-05'
ARCHIVE_REVIEW_DATE = '2026-11-04'


@dataclass(frozen=True)
class EquityCover:
    symbol: str
    security: str
    filed: str
    path: str


# Dated issuer cover rows include the exact class on Nasdaq and Nasdaq Texas.
_CSTL_Q3_COVER = EquityCover('CSTL', 'Common stock', '2026-11-05', '1447362/000162828026071038/cstl-20260930.htm')
_NUTX_Q3_COVER = EquityCover('NUTX', 'Common stock', '2026-11-05', '1479681/000162828026070993/nutx-20260930.htm')
_RUSH_COVER = '1012019/000143774926026588/rusha20260630_10q.htm'
EQUITY_COVERS = (
    EquityCover('ACDC', 'Class A common stock', '2026-08-06', '1881487/000119312526337969/acdc-20260630.htm'),
    EquityCover('APA', 'Common stock', '2026-08-06', '1841666/000184166626000053/apa-20260630.htm'),
    _CSTL_Q3_COVER,
    EquityCover('HBAN', 'Common stock', '2026-10-27', '49196/000004919626000090/hban-20260930.htm'),
    EquityCover('JBHT', 'Common stock', '2026-10-23', '728535/000143774926033365/jbht20260930_10q.htm'),
    EquityCover('NDAQ', 'Common stock', '2026-10-22', '1120193/000112019326000020/ndaq-20260930.htm'),
    _NUTX_Q3_COVER,
    EquityCover('RMIX', 'Class A common stock', '2026-08-14', '2094433/000119312526352341/rmix-20260630.htm'),
    EquityCover('ROAD', 'Class A common stock', '2026-08-07', '1718227/000162828026054661/road-20260630.htm'),
    EquityCover('RUSHA', 'Class A common stock', '2026-08-07', _RUSH_COVER),
    EquityCover('RUSHB', 'Class B common stock', '2026-08-07', _RUSH_COVER),
    EquityCover('SPCX', 'Class A common stock', '2026-10-22', '1181412/000162828026066880/spcx-20260930.htm'),
)


@dataclass(frozen=True)
class FundCohort:
    issuer: str
    certificate_date: str
    effective: str
    certificate_path: str
    identity_url: str
    identity_label: str
    members: tuple[tuple[str, str], ...]


FUND_COHORTS = (
    FundCohort(
        'Victory Portfolios II', '2026-10-26', '2026-10-27',
        '1547580/000135445726001022/VictoryPortfoliosII_8A_Cert.pdf',
        NASDAQ_VICTORY_NOTICE, 'Nasdaq ticker and effective-date notice',
        (
            ('ABI', 'VictoryShares Pioneer Asset-Based Income ETF'),
            ('CDC', 'VictoryShares US EQ Income Enhanced Volatility Wtd ETF'),
            ('CDL', 'VictoryShares US Large Cap High Div Volatility Wtd ETF'),
            ('CFA', 'VictoryShares US 500 Volatility Wtd ETF'),
            ('CFO', 'VictoryShares US 500 Enhanced Volatility Wtd ETF'),
            ('CSB', 'VictoryShares US Small Cap High Div Volatility Wtd ETF'),
            ('GFLW', 'VictoryShares Free Cash Flow Growth ETF'),
            ('GLOW', 'VictoryShares WestEnd Global Equity ETF'),
            ('GRIN', 'VictoryShares International Free Cash Flow Growth ETF'),
            ('IFLO', 'VictoryShares International Free Cash Flow ETF'),
            ('MODL', 'VictoryShares WestEnd U.S. Sector ETF'),
            ('SFLO', 'VictoryShares Small Cap Free Cash Flow ETF'),
            ('UBND', 'VictoryShares Core Plus Bond ETF'),
            ('UCRD', 'VictoryShares Corporate Bond ETF'),
            ('UEVM', 'VictoryShares Emerging Markets Value Momentum ETF'),
            ('UITB', 'VictoryShares Core Intermediate Bond ETF'),
            ('UIVM', 'VictoryShares International Value Momentum ETF'),
            ('ULVM', 'VictoryShares US Value Momentum ETF'),
            ('USTB', 'VictoryShares Short-Term Bond ETF'),
            ('USVM', 'VictoryShares US Small Mid Cap Value Momentum ETF'),
            ('VFLO', 'VictoryShares Free Cash Flow ETF'),
            ('VMHY', 'VictoryShares Municipal High Yield ETF'),
            ('VMSD', 'VictoryShares Short-Duration Municipal ETF'),
            ('VSDA', 'VictoryShares Dividend Accelerator ETF'),
            ('VSMV', 'VictoryShares US Multi-Factor Minimum Volatility ETF'),
        ),
    ),
    FundCohort(
        'ETF Opportunities Trust', '2026-10-30', '2026-11-02',
        '1771146/000135445726001040/ETFOpportunities8A_Cert.pdf',
        SEC_ARCHIVE + '1771146/000177114626002155/etfot-appliedfinanceivsetf.htm',
        'SEC prospectus supplement',
        (
            ('IVSI', 'Applied Finance IVS International Large ETF'),
            ('IVSS', 'Applied Finance IVS US SMID ETF'),
            ('IVSX', 'Applied Finance IVS International SMID ETF'),
        ),
    ),
)


def nasdaq_texas_review_markdown() -> str:
    stocks = len(EQUITY_COVERS)
    funds = sum(len(group.members) for group in FUND_COHORTS)
    return f"""
Equity and fund evidence reviewed {REVIEW_DATE} · BWIN follow-up rechecked 2026-11-12 · Nasdaq Texas, LLC is a separate venue from TXSE and NYSE Texas.

- **Operations after conversion confirmed.** Nasdaq BX became Nasdaq Texas on 2026-02-13. SEC approved new listing standards on 2026-02-27, and Nasdaq announced the dual-listing launch on 2026-03-05. Nasdaq Trader reports positive NTX matched volume for September 2026. [SEC conversion filing]({SEC_CONVERSION}) · [SEC order 34-104907]({SEC_STANDARDS}) · [Nasdaq launch]({NASDAQ_LAUNCH}) · [Nasdaq matched volume]({NASDAQ_VOLUME})
- **{stocks + funds} securities with dated dual-listing evidence.** {stocks} stock classes appear on both venues in issuer covers. {funds} ETF identities match exchange certifications and published effective dates. These counts cover the reviewed records.
- **Admission follow-up · 2 of 3 independently confirmed.** The November 5 SEC covers show CSTL and NUTX dual registration as filed. BWIN admission remains open.
- **Full current roster remains unverified.** The September SEC notice gives a Q2 2027 primary-listing target, subject to a Nasdaq announcement. The review found no primary listing to confirm. Historical continuity and individual first executions also remain open. [SEC primary-listing notice]({SEC_PRIMARY_TARGET})
"""


def nasdaq_texas_detail_markdown() -> str:
    follow_up = f"""**Admission follow-up · Dated SEC evidence**

The public Nasdaq Trader archives reviewed through {ARCHIVE_REVIEW_DATE} yielded no listing-effective notice for these three securities. The November 5 SEC covers confirm two registrations as filed. Historical start dates remain unverified. [Equity Trader]({NASDAQ_ARCHIVE}2) · [Regulatory]({NASDAQ_ARCHIVE}6) · [Corporate Action]({NASDAQ_ARCHIVE}105) · [ETP]({NASDAQ_ARCHIVE}112)

- **BWIN** · Class A common stock · Planned 2026-05-11. Earlier SEC covers reviewed through {ARCHIVE_REVIEW_DATE} named only Nasdaq Global Select Market for this class, including the 2026-10-27 Form 8-K. Rechecked 2026-11-12: the November 9 Form 10-Q cover for the period ended 2026-09-30 still names only Nasdaq Global Select Market for Class A common stock. Nasdaq Texas approval was subject to official notice of issuance. Admission remains open.
  [Form 8-A]({SEC_ARCHIVE}1781755/000178175526000037/baldwin202657form8-a.htm) · [SEC exchange certification]({SEC_ARCHIVE}1781755/000087679626000012/BWIN_8A_Cert_1781755.pdf) · [October 27 Form 8-K]({SEC_ARCHIVE}1781755/000178175526000062/bwin-20261027.htm) · [November 9 Form 10-Q]({SEC_ARCHIVE}1781755/000178175526000068/bwin-20260930.htm#f-16)
- **CSTL** · Common stock · Planned 2026-08-17 in Form 8-A. The exchange approved the class subject to official notice of issuance.
  The [Form 10-Q filed {_CSTL_Q3_COVER.filed}]({SEC_ARCHIVE + _CSTL_Q3_COVER.path}) for the period ended 2026-09-30 names The Nasdaq Global Market and Nasdaq Texas, LLC for the same common stock.
  [Prior Form 10-Q filed 2026-07-30]({SEC_ARCHIVE}1447362/000162828026051052/cstl-20260630.htm) names only The Nasdaq Global Market and predates approval.
  [Form 8-A]({SEC_ARCHIVE}1447362/000162828026056924/a8-axnasdaqtexaslistingxau.htm) · [SEC exchange certification]({SEC_ARCHIVE}1447362/000087679626000017/8A_CERT_CSTL_0001447362.pdf)
- **NUTX** · Common stock · Planned 2026-09-23. The 2026-09-22 exchange certification records approval.
  The [Form 10-Q filed {_NUTX_Q3_COVER.filed}]({SEC_ARCHIVE + _NUTX_Q3_COVER.path}) for the period ended 2026-09-30 names The Nasdaq Stock Market LLC and Nasdaq Texas, LLC for the same common stock.
  [Prior Form 10-Q filed 2026-08-06]({SEC_ARCHIVE}1479681/000162828026054268/nutx-20260630.htm) names only The Nasdaq Stock Market LLC and predates approval.
  [Form 8-A]({SEC_ARCHIVE}1479681/000162828026063013/nutex_healthxformx8xa12b.htm) · [SEC exchange certification]({SEC_ARCHIVE}1479681/000087679626000018/NUTX_8A_Cert_0001479681.pdf) · [SEC issuer index](https://www.sec.gov/edgar/browse/?CIK=1479681)

**Current roster**

The 2026-11-04 public symbol directories have no Nasdaq Texas dual-listing field. Nasdaq Trader separately documents NTX trading-system changes. The venue's public pages and five June–October SEC Form 1 amendments did not yield a complete dated roster. [Nasdaq Texas](https://www.nasdaq.com/nasdaq-texas) · [Directory definitions]({NASDAQ_SYMBOL_DEFINITIONS}) · [October Form 1 amendment]({SEC_OCTOBER_FORM_1})"""
    equity = '\n'.join(
        f'- **{row.symbol}** · {row.security} · [10-Q, {row.filed}]({SEC_ARCHIVE + row.path})'
        for row in EQUITY_COVERS
    )
    sections = [follow_up, f'**Common stock · Dual registration as filed**\n\n{equity}']
    for group in FUND_COHORTS:
        members = '\n'.join(f'- **{symbol}** · {name}' for symbol, name in group.members)
        sections.append(
            f'**{group.issuer} · {len(group.members)} ETFs**\n\n'
            f'Certified {group.certificate_date} · Published effective date {group.effective}. '
            f'[SEC exchange certificate]({SEC_ARCHIVE + group.certificate_path}) · '
            f'[{group.identity_label}]({group.identity_url})\n\n{members}'
        )
    return '\n\n'.join(sections)
