"""Dated TXSE operations and security identity review for Discover."""

from dataclasses import dataclass

SEC_ORDER = 'https://www.sec.gov/files/rules/other/2025/34-104146.pdf'
TXSE = 'https://www.txse.com'
TXSE_SCHEDULE = TXSE + '/alerts/july-2026-symbol-rollout-schedule'
TXSE_LAUNCH = TXSE + '/press/texas-stock-exchange-celebrates-successful-launch-of-trading'
TXSE_ALERT_ARCHIVE = TXSE + '/alerts-notices'
TXSE_JULY_TEST_NOTICE = TXSE + '/alerts/5059533f-8b82-4a4f-944c-7b126dbb7176'
TXSE_JULY_10_SYMBOLS = 'https://download.web.txse.com/historical/symbols/public_symbols_2026_07_10.txt'
TXSE_MARKET_DATA = TXSE + '/market-data'
TXSE_RULE_605 = TXSE + '/regulations/605-reports'
TXSE_JULY_605 = 'https://download.web.txse.com/605reports/F202607.zip'
CBOE_DAILY_VOLUME = 'https://cdn.cboe.com/resources/us/equities/market-statistics/historical-market-volume/market_history_2026.csv'
TXSE_ETP_START = TXSE + '/press/texas-stock-exchange-celebrates-transfer-of-texas-capital-s-txs-and-oilt-exchange-traded-funds'
TXSE_CORPORATE_START = TXSE + '/press/texas-stock-exchange-celebrates-move-of-energy-transfer-partnership-s-primary-listings'
TXSE_DIRECTORY = TXSE + '/all-listings'
TXSE_SYMBOLS = 'https://download.web.txse.com/historical/symbols/public_symbols_2026_11_04.txt'
NASDAQ_OTHER_LISTED = 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
SCHW_ALERT = TXSE + '/alerts/b73ae818-f4d2-4437-8cc9-8370719ecbe2'
SCHW_ACTION = 'https://download.web.txse.com/calf/TXSE_MAF/2026/10/TXSE_MAF_20261006_2000_FINAL_NO_CUSIP.csv'
SCHW_COVER = 'https://www.sec.gov/Archives/edgar/data/316709/000031670926000035/schw-20261015.htm'
REVIEW_DATE = '2026-11-04'
DIRECTORY_DATE = '2026-11-03'
DIRECTORY_LISTINGS = 23
EXCLUDED_TEST_ROWS = 68


@dataclass(frozen=True)
class SecurityIdentity:
    symbol: str
    issuer: str
    kind: str
    security: str
    form: str
    filed: str
    sec_path: str

    @property
    def source_url(self) -> str:
        return 'https://www.sec.gov/Archives/edgar/data/' + self.sec_path


# This set joins the dated TXSE root and suffix to SEC class evidence.
# A shared filing can register multiple distinct securities.
_ET_CERT = '1276187/000205484726000015/ET_8ACert.pdf'
_TEMA_PROSPECTUS = '1944285/000182912626011382/temaetftrust_497.htm'
_TEXAS_CAPITAL_FUNDS_CERT = '1972459/000205484726000008/OILT_TXS8ACert.pdf'
TXSE_IDENTITIES = (
    SecurityIdentity('CECO', 'CECO Environmental Corp.', 'Common stock', 'Common stock', 'CERT', '2026-10-16',
                     '3197/000205484726000045/CECO8ACERT.pdf'),
    SecurityIdentity('CTAG', 'Calamos ETF Trust', 'ETF', 'Calamos Timpani Active SMID Growth ETF', 'CERT', '2026-09-15',
                     '1579881/000205484726000004/CTAG8ACert.pdf'),
    SecurityIdentity('DDS', "Dillard's, Inc.", 'Common stock', 'Class A common stock', 'CERT', '2026-09-30',
                     '28917/000205484726000023/DDS_8ACert.pdf'),
    SecurityIdentity('DDT', "Dillard's Capital Trust I", 'Trust capital securities',
                     "7.50% capital securities guaranteed by Dillard's, Inc.", 'CERT', '2026-09-30',
                     '28917/000205484726000025/DDT_8ACert.pdf'),
    SecurityIdentity('ET', 'Energy Transfer LP', 'Common units', 'Common units', 'CERT', '2026-09-30', _ET_CERT),
    SecurityIdentity('ET-PRI', 'Energy Transfer LP', 'Preferred units',
                     '9.250% Series I fixed-rate perpetual preferred units', 'CERT', '2026-09-30', _ET_CERT),
    SecurityIdentity('FIFT', 'Northern Lights Fund Trust III', 'ETF', 'HCM Select 50 ETF', 'CERT', '2026-10-16',
                     '1537140/000205484726000047/FIFT8ACert.pdf'),
    SecurityIdentity('IBOC', 'International Bancshares Corporation', 'Common stock', 'Common stock', 'CERT',
                     '2026-10-13', '315709/000205484726000041/IBOC8ACert.pdf'),
    SecurityIdentity('ICOM', 'Tema ETF Trust', 'ETF', 'Tema Commodity Income ETF', '497', '2026-10-21',
                     _TEMA_PROSPECTUS),
    SecurityIdentity('ILS', 'ETF Opportunities Trust', 'ETF', 'Brookmont Catastrophic Bond ETF', 'CERT', '2026-09-16',
                     '1771146/000205484726000013/ILS_TXS8ACert.pdf'),
    SecurityIdentity('OBK', 'Origin Bancorp, Inc.', 'Common stock', 'Common stock', 'CERT', '2026-10-09',
                     '1516912/000205484726000039/OBK8ACert.pdf'),
    SecurityIdentity('OILT', 'Texas Capital Funds Trust', 'ETF', 'Texas Capital Texas Oil Index ETF', 'CERT',
                     '2026-09-15', _TEXAS_CAPITAL_FUNDS_CERT),
    SecurityIdentity('PWRX', 'Ultimus Managers Trust', 'ETF', 'Westwood Salient Enhanced Power & Infrastructure ETF',
                     '8-A12B', '2026-08-10', '1545440/000158064226005055/westwoodpwrx_8a12b.htm'),
    SecurityIdentity('SCHW', 'The Charles Schwab Corporation', 'Common stock', 'Common stock, secondary listing',
                     '8-K', '2026-10-15', '316709/000031670926000035/schw-20261015.htm'),
    SecurityIdentity('SUN', 'Sunoco LP', 'Common units', 'Common limited-partner units', 'CERT', '2026-09-30',
                     '1552275/000205484726000021/SUN_8ACert.pdf'),
    SecurityIdentity('SUNC', 'SunocoCorp LLC', 'Common units', 'Common LLC units', 'CERT', '2026-09-30',
                     '2089661/000205484726000019/SUNC_8ACert.pdf'),
    SecurityIdentity('TCBI', 'Texas Capital Bancshares, Inc.', 'Common stock', 'Common stock', 'CERT', '2026-10-07',
                     '1077428/000205484726000035/TCBI8ACert.pdf'),
    SecurityIdentity('TCBI-PRB', 'Texas Capital Bancshares, Inc.', 'Depositary shares',
                     'Depositary shares, each representing 1/40 of a Series B preferred share', 'CERT', '2026-10-08',
                     '1077428/000205484726000037/TCBIPRB8ACert.pdf'),
    SecurityIdentity('THRU', 'Tema ETF Trust', 'ETF', 'Tema Commodity Infrastructure ETF', '497', '2026-10-21',
                     _TEMA_PROSPECTUS),
    SecurityIdentity('TXS', 'Texas Capital Funds Trust', 'ETF', 'Texas Capital Texas Equity Index ETF', 'CERT',
                     '2026-09-15', _TEXAS_CAPITAL_FUNDS_CERT),
    SecurityIdentity('USAC', 'USA Compression Partners, LP', 'Common units', 'Common units', 'CERT', '2026-09-30',
                     '1522727/000205484726000017/USAC_8ACert.pdf'),
    SecurityIdentity('WSLS', 'WisdomTree Trust', 'ETF', 'WisdomTree Efficient Long/Short U.S. SmallCap Equity Fund',
                     'CERT', '2026-10-06', '1350487/000205484726000029/WSLS8ACert.pdf'),
    SecurityIdentity('WTAL', 'WisdomTree Trust', 'ETF', 'WisdomTree Global Alpha Fund', 'CERT', '2026-10-06',
                     '1350487/000205484726000031/WTAL8ACert.pdf'),
)


def txse_review_markdown() -> str:
    etfs = sum(row.kind == 'ETF' for row in TXSE_IDENTITIES)
    return f"""
Reviewed {REVIEW_DATE} · Texas Stock Exchange LLC and NYSE Texas are separate venues.

- **Live trading confirmed by 2026-07-31.** The SEC granted registration on 2025-09-30. TXSE confirmed the July rollout was complete. [SEC order]({SEC_ORDER}) · [TXSE launch confirmation]({TXSE_LAUNCH})
- **First execution date remains unverified.** TXSE began the rollout with test symbols on 2026-07-06 and scheduled live trading for 2026-07-10. Cboe reports 100 TXSE trades on 2026-07-10. The review found no TXSE trade-level record or notice explicitly confirming the first day of executions. [Rollout schedule]({TXSE_SCHEDULE}) · [Cboe daily trade counts]({CBOE_DAILY_VOLUME})
- **Primary listings confirmed.** TXSE reported TXS and OILT began trading on 2026-09-16. It confirmed its first corporate primary listings on 2026-10-05. [ETF launch]({TXSE_ETP_START}) · [Corporate listing launch]({TXSE_CORPORATE_START})
- **{len(TXSE_IDENTITIES)} of {DIRECTORY_LISTINGS} security identities verified.** The TXSE directory dated {DIRECTORY_DATE} contains {etfs} ETFs and {len(TXSE_IDENTITIES) - etfs} other securities. TXSE and Nasdaq files cross-check 22 primary listings on {REVIEW_DATE}. The TXSE symbol file included {EXCLUDED_TEST_ROWS} test rows, all excluded. [TXSE listing directory]({TXSE_DIRECTORY}) · [Dated TXSE symbol file]({TXSE_SYMBOLS}) · [Nasdaq directory]({NASDAQ_OTHER_LISTED})
- **SCHW · Separate secondary listing.** TXSE recorded the common stock's admission effective 2026-10-07. The 2026-10-15 SEC cover shows NYSE and TXSE. The 22 flagged rows omit this secondary listing. [TXSE dual-listing notice]({SCHW_ALERT}) · [TXSE market action]({SCHW_ACTION}) · [SCHW SEC cover]({SCHW_COVER})

This is a dated listing review. Changes after the directory date and continuous listing history require separate evidence. Symbols eligible to trade on TXSE include securities listed elsewhere.
"""


def txse_first_trade_markdown() -> str:
    return f"""
**First-trade sources reviewed {REVIEW_DATE}**

- **TXSE notices.** The July 6 update kept July 10 on the schedule. No July notice reviewed confirms an execution on July 10. The July 31 release confirms the completed rollout. [Test-symbol update]({TXSE_JULY_TEST_NOTICE}) · [TXSE alerts archive]({TXSE_ALERT_ARCHIVE})
- **TXSE symbol files.** July 6–9 contain only test symbols. The July 10 file adds PBA, PDFS, SPHD, SRRK and VCYT as non-test symbols. These files establish trading eligibility for the published symbols. [July 10 symbol file]({TXSE_JULY_10_SYMBOLS})
- **TXSE execution data.** The Market Data Center describes the BALE and FEED execution feeds. The review found no public July 10 trade file there. The July Rule 605 download returned HTTP 403. Rule 605 reports aggregate executions by month. [TXSE Market Data Center]({TXSE_MARKET_DATA}) · [Rule 605 index]({TXSE_RULE_605}) · [July download]({TXSE_JULY_605})
- **Cboe daily counts.** July 10 is the earliest positive TXSE row in the reviewed 2026 file. July 6–9 have missing rows for TXSE. The counts corroborate July 10 activity at venue level and supply neither individual executions nor complete earlier coverage. [Cboe daily trade counts]({CBOE_DAILY_VOLUME})
"""


def txse_identity_markdown() -> str:
    sections = []
    for title, is_etf in (('Other securities', False), ('Exchange-traded funds', True)):
        rows = [
            f'- **{row.symbol}** · {row.issuer} · {row.security} · [{row.form}, {row.filed}]({row.source_url})'
            for row in TXSE_IDENTITIES if (row.kind == 'ETF') == is_etf
        ]
        sections.append(f'**{title}**\n\n' + '\n'.join(rows))
    return '\n\n'.join(sections)
