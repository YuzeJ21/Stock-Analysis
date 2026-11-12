"""Reduced findings from the November 12 SEC and Nasdaq Trader listing review."""

from src.online_company_identity import _mode_reason
from src.online_us_universe import EXCHANGE_URL, MAP_URL
from src.us_listing_receipt_audit import _SOURCES

ABR_COVER = 'https://www.sec.gov/Archives/edgar/data/1253986/000125398626000064/abr-20261030.htm'
ALUR_REMOVAL = 'https://www.sec.gov/Archives/edgar/data/876661/000087666126000826/ruleprovisionnotice.htm'
ALUR_SUBMISSIONS = 'https://data.sec.gov/submissions/CIK0001964979.json'
GOOG_COVER = 'https://www.sec.gov/Archives/edgar/data/1652044/000119312526449835/d174184d8k.htm'
ADSEW_COVER = 'https://www.sec.gov/Archives/edgar/data/1879248/000121390026057891/ea0290629-20f_adstec.htm'
PFBC_SUBMISSIONS = 'https://data.sec.gov/submissions/CIK0001492165.json'


def listing_gap_review_markdown() -> str:
    if _mode_reason('research'):
        return ''
    return f"""
**2026-11-12 snapshot · 13,791 observed listing records · 38 test issues excluded**

- **544 SEC-only records.** These rows carry an exchange in the SEC map and lack a confirmed symbol join to either directory. Four were reviewed, with 540 still unreviewed.
- **282 unresolved directory types.** 246 had no recognized instrument wording, 19 had ambiguous wording, and 17 had conflicting flag and description evidence. Three were reviewed, with 279 still unreviewed.

**Dated findings**

- **ABR-PD, ABR-PE and ABR-PF · Three NYSE preferred share classes matched.** Arbor Realty's October 30 Form 8-K identifies Series D, E and F separately. The November 12 directory uses `ABR$D`, `ABR$E` and `ABR$F` for those classes. [SEC cover]({ABR_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
- **ALUR · NYSE removal evidence.** The October 13 Form 25 attachment gives October 26 as the removal date for the common stock and warrants and reports a March 6 trading suspension. SEC issuer submissions show OTC while the exchange map still associates ALUR with NYSE. [Form 25 attachment]({ALUR_REMOVAL}) · [SEC submissions]({ALUR_SUBMISSIONS})
- **GOOG · Class C Capital Stock.** Alphabet's November 5 Form 8-K identifies this exact Nasdaq class. The directory rule leaves it unknown. [SEC cover]({GOOG_COVER})
- **ADSEW · Nasdaq warrant.** ADS-TEC's May 15 Form 20-F identifies warrants to purchase ordinary shares under ADSEW. It lists the ordinary shares separately as ADSE. [SEC cover]({ADSEW_COVER})
- **PFBC · Type remains unresolved.** The directory name contains both preferred and common stock wording. The SEC submissions screen returned no issuer report with an exact cover for this check. [SEC submissions]({PFBC_SUBMISSIONS})

The reviewed cases apply to the stated sources and dates and are for personal inspection. The inventory and financial counts use their original inputs. Full U.S. coverage remains unverified. [Nasdaq directory]({_SOURCES[0][2]}) · [SEC ticker map]({MAP_URL}) · [SEC exchange map]({EXCHANGE_URL})
"""
