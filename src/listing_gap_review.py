"""Reduced findings from the November 12 SEC and Nasdaq Trader listing review."""

from src.online_company_identity import _mode_reason
from src.online_us_universe import EXCHANGE_URL, MAP_URL
from src.us_listing_receipt_audit import _SOURCES

ABR_COVER = 'https://www.sec.gov/Archives/edgar/data/1253986/000125398626000064/abr-20261030.htm'
AGM_COVER = 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000143/agm-20261112.htm'
AGM_QUARTER = 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000139/agm-20260930.htm'
ALUR_REMOVAL = 'https://www.sec.gov/Archives/edgar/data/876661/000087666126000826/ruleprovisionnotice.htm'
ALUR_SUBMISSIONS = 'https://data.sec.gov/submissions/CIK0001964979.json'
GOOG_COVER = 'https://www.sec.gov/Archives/edgar/data/1652044/000119312526449835/d174184d8k.htm'
ADSEW_COVER = 'https://www.sec.gov/Archives/edgar/data/1879248/000121390026057891/ea0290629-20f_adstec.htm'
PFBC_FDIC_QUARTER = 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12041/attachment/1'
PFBC_FDIC_ANNUAL = 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11872/attachment/1'


def listing_gap_review_markdown() -> str:
    if _mode_reason('research'):
        return ''
    return f"""
**2026-11-12 snapshot · 13,791 observed listing records · 38 test issues excluded**

- **544 SEC-only records.** These rows carry an exchange in the SEC map and lack a confirmed symbol join to either directory. Ten were reviewed, with 534 still unreviewed.
- **282 unresolved directory types.** 246 had no recognized instrument wording, 19 had ambiguous wording, and 17 had conflicting flag and description evidence. Three now have dated class evidence, with 279 still unreviewed.

**Dated findings**

- **ABR-PD, ABR-PE and ABR-PF · Three NYSE preferred share classes matched.** Arbor Realty's October 30 Form 8-K identifies Series D, E and F separately. The November 12 directory uses `ABR$D`, `ABR$E` and `ABR$F` for those classes. [SEC cover]({ABR_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
- **Farmer Mac Series D–I · Six NYSE preferred share classes matched.** The November 12 Form 8-K, November 6 Form 10-Q and November 12 Nasdaq Trader directory identify the same six non-cumulative preferred classes. The symbols below follow series order. [Farmer Mac 8-K]({AGM_COVER}) · [Farmer Mac 10-Q]({AGM_QUARTER}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
  - SEC map · `AGM-PD`, `AGM-PE`, `AGM-PF`, `AGM-PG`, `AGM-PH`, `AGM-PI`
  - Filing cover · `AGM.PRD`, `AGM.PRE`, `AGM.PRF`, `AGM.PRG`, `AGM.PRH`, `AGM.PRI`
  - Directory · `AGM$D`, `AGM$E`, `AGM$F`, `AGM$G`, `AGM$H`, `AGM$I`
- **ALUR · NYSE removal evidence.** The October 13 Form 25 attachment gives October 26 as the removal date for the common stock and warrants and reports a March 6 trading suspension. SEC issuer submissions show OTC while the exchange map still associates ALUR with NYSE. [Form 25 attachment]({ALUR_REMOVAL}) · [SEC submissions]({ALUR_SUBMISSIONS})
- **GOOG · Class C Capital Stock.** Alphabet's November 5 Form 8-K identifies this exact Nasdaq class. The directory rule leaves it unknown. [SEC cover]({GOOG_COVER})
- **ADSEW · Nasdaq warrant.** ADS-TEC's May 15 Form 20-F identifies warrants to purchase ordinary shares under ADSEW. It lists the ordinary shares separately as ADSE. [SEC cover]({ADSEW_COVER})
- **PFBC · Nasdaq common stock confirmed as filed.** Preferred Bank's FDIC Form 10-Q filed November 9 for the quarter ended September 30 lists PFBC as no-par-value common stock on Nasdaq. The March 2 Form 10-K reports the same class, ticker and venue. Both covers carry FDIC certificate 33539. The directory rule still leaves PFBC unknown. [FDIC Form 10-Q]({PFBC_FDIC_QUARTER}) · [FDIC Form 10-K]({PFBC_FDIC_ANNUAL})

The reviewed cases apply to the stated sources and dates and are for personal inspection. Current trading status and financial eligibility require separate checks. Full U.S. coverage remains unverified. [Nasdaq directory]({_SOURCES[0][2]}) · [SEC ticker map]({MAP_URL}) · [SEC exchange map]({EXCHANGE_URL})
"""
