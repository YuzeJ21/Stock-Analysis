"""Reduced findings from the November 12 SEC and Nasdaq Trader listing review."""

from src.online_company_identity import _mode_reason
from src.online_us_universe import EXCHANGE_URL, MAP_URL
from src.us_listing_receipt_audit import _SOURCES

ABR_COVER = 'https://www.sec.gov/Archives/edgar/data/1253986/000125398626000064/abr-20261030.htm'
AGM_COVER = 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000143/agm-20261112.htm'
AGM_QUARTER = 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000139/agm-20260930.htm'
TRITON_COVER = 'https://www.sec.gov/Archives/edgar/data/1660734/000166073426000005/trtn-20251231.htm'
TRITON_INTERIM = 'https://www.sec.gov/Archives/edgar/data/1660734/000162828026071407/trtn-20260930.htm'
TRITON_SERIES_G_NYSE = 'https://www.sec.gov/Archives/edgar/data/1660734/000087666126000041/TRTNPRG011326.pdf'
RITHM_COVER = 'https://www.sec.gov/Archives/edgar/data/1556593/000155659326000035/nrz-20260930.htm'
RITHM_SERIES_F_NYSE = 'https://www.sec.gov/Archives/edgar/data/1556593/000087666126000052/RITMPRF012126.pdf'
ANNALY_COVER = 'https://www.sec.gov/Archives/edgar/data/1043219/000104321926000083/nly-20260930.htm'
ANNALY_SERIES_F_TERMS = 'https://www.sec.gov/Archives/edgar/data/1043219/000119312517235069/d417558dfwp.htm'
ANNALY_SERIES_I_REDEMPTION = 'https://www.sec.gov/Archives/edgar/data/1043219/000104321926000070/nly-20261002.htm'
ANNALY_SERIES_I_NYSE = 'https://www.sec.gov/Archives/edgar/data/876661/000087666126000807/ruleprovisionnotice.htm'
ALUR_REMOVAL = 'https://www.sec.gov/Archives/edgar/data/876661/000087666126000826/ruleprovisionnotice.htm'
ALUR_SUBMISSIONS = 'https://data.sec.gov/submissions/CIK0001964979.json'
GOOG_COVER = 'https://www.sec.gov/Archives/edgar/data/1652044/000119312526449835/d174184d8k.htm'
ADSEW_COVER = 'https://www.sec.gov/Archives/edgar/data/1879248/000121390026057891/ea0290629-20f_adstec.htm'
PFBC_FDIC_QUARTER = 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12041/attachment/1'
PFBC_FDIC_ANNUAL = 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11872/attachment/1'
PFBC_FDIC_CURRENT_REPORT = 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12028/attachment/1'
PFBC_FDIC_AMENDMENT = 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11687/attachment/1'
PFBC_FDIC_INDEX = 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/cert/33539'


def listing_gap_review_markdown() -> str:
    if _mode_reason('research'):
        return ''
    return f"""
**2026-11-12 snapshot · 13,791 observed listing records · 38 test issues excluded**

- **544 SEC-only records.** These rows carry an exchange in the SEC map and lack a confirmed symbol join to either directory. 26 were reviewed, with 518 still unreviewed.
- **282 unresolved directory types.** 246 had no recognized instrument wording, 19 had ambiguous wording, and 17 had conflicting flag and description evidence. Four now have dated class evidence, with 278 still unreviewed.

**Dated findings**

- **Rithm Capital Series A–F · Six NYSE preferred share classes matched.** The November 2 Form 10-Q and November 12 Nasdaq Trader directory agree on six direct preferred stock classes. The percentages in the class titles identify the securities. Current yields are outside this review. [Rithm Form 10-Q]({RITHM_COVER}) · [NYSE Series F certification]({RITHM_SERIES_F_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
  - SEC map · `RITM-PA`, `RITM-PB`, `RITM-PC`, `RITM-PD`, `RITM-PE`, `RITM-PF`
  - Filing cover · `RITM PR A`, `RITM PR B`, `RITM PR C`, `RITM PR D`, `RITM PR E`, `RITM PR F`
  - Directory · `RITM$A`, `RITM$B`, `RITM$C`, `RITM$D`, `RITM$E`, `RITM$F`
- **Annaly Series F, G and J · Three NYSE preferred share classes matched.** The October 28 Form 10-Q identifies all three classes. The shortened Series F directory description matches the issuer, NYSE, series and title rate. The filed term sheet gives `NLYPrF` as the NYSE listing symbol. The directory's CQS spelling is `NLYpF`, and its description rule still leaves `NLY$F` unknown. [Annaly Form 10-Q]({ANNALY_COVER}) · [Series F term sheet]({ANNALY_SERIES_F_TERMS})
  - SEC map · `NLY-PF`, `NLY-PG`, `NLY-PJ`
  - Filing cover · `NLY.F`, `NLY.G`, `NLY.J`
  - Directory · `NLY$F`, `NLY$G`, `NLY$J`
  - Series I was redeemed October 1. NYSE's notice specified removal at the October 12 opening. Series I is excluded from the reviewed counts. [Annaly Form 8-K]({ANNALY_SERIES_I_REDEMPTION}) · [NYSE removal notice]({ANNALY_SERIES_I_NYSE})
- **ABR-PD, ABR-PE and ABR-PF · Three NYSE preferred share classes matched.** Arbor Realty's October 30 Form 8-K identifies Series D, E and F separately. The November 12 directory uses `ABR$D`, `ABR$E` and `ABR$F` for those classes. [SEC cover]({ABR_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
- **Farmer Mac Series D–I · Six NYSE preferred share classes matched.** The November 12 Form 8-K, November 6 Form 10-Q and November 12 Nasdaq Trader directory identify the same six non-cumulative preferred classes. The symbols below follow series order. [Farmer Mac 8-K]({AGM_COVER}) · [Farmer Mac 10-Q]({AGM_QUARTER}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
  - SEC map · `AGM-PD`, `AGM-PE`, `AGM-PF`, `AGM-PG`, `AGM-PH`, `AGM-PI`
  - Filing cover · `AGM.PRD`, `AGM.PRE`, `AGM.PRF`, `AGM.PRG`, `AGM.PRH`, `AGM.PRI`
  - Directory · `AGM$D`, `AGM$E`, `AGM$F`, `AGM$G`, `AGM$H`, `AGM$I`
- **Triton Series A–G · Seven NYSE preference share classes matched.** Triton's February 20 Form 20-F cover and the November 12 Nasdaq Trader directory agree on the series and stated rates. Its November 6 interim statements corroborate the classes as of September 30. Series G was issued in January 2026 and has its own NYSE listing certification. [Triton 20-F]({TRITON_COVER}) · [Triton interim statements]({TRITON_INTERIM}) · [NYSE Series G certification]({TRITON_SERIES_G_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
  - SEC map · `TRTN-PA`, `TRTN-PB`, `TRTN-PC`, `TRTN-PD`, `TRTN-PE`, `TRTN-PF`, `TRTN-PG`
  - Filing cover · `TRTN PRA`, `TRTN PRB`, `TRTN PRC`, `TRTN PRD`, `TRTN PRE`, `TRTN PRF`, `TRTN PRG`
  - Directory · `TRTN$A`, `TRTN$B`, `TRTN$C`, `TRTN$D`, `TRTN$E`, `TRTN$F`, `TRTN$G`
- **ALUR · NYSE removal evidence.** The October 13 Form 25 attachment gives October 26 as the removal date for the common stock and warrants and reports a March 6 trading suspension. SEC issuer submissions show OTC while the exchange map still associates ALUR with NYSE. [Form 25 attachment]({ALUR_REMOVAL}) · [SEC submissions]({ALUR_SUBMISSIONS})
- **GOOG · Class C Capital Stock.** Alphabet's November 5 Form 8-K identifies this exact Nasdaq class. The directory rule leaves it unknown. [SEC cover]({GOOG_COVER})
- **ADSEW · Nasdaq warrant.** ADS-TEC's May 15 Form 20-F identifies warrants to purchase ordinary shares under ADSEW. It lists the ordinary shares separately as ADSE. [SEC cover]({ADSEW_COVER})
- **PFBC · Nasdaq common stock confirmed as filed.** Preferred Bank's FDIC Form 10-Q filed November 9 for the quarter ended September 30 lists PFBC as no-par-value common stock on Nasdaq. The March 2 Form 10-K reports the same class, ticker and venue. Both covers carry FDIC certificate 33539. The directory rule still leaves PFBC unknown. [FDIC Form 10-Q]({PFBC_FDIC_QUARTER}) · [FDIC Form 10-K]({PFBC_FDIC_ANNUAL})
- **PFBC IRS number · Unreconciled.** Six quarterly covers from 2025 and 2026 show `95-4340119`. The 2024 and 2025 annual covers and October 27 Form 8-K show `95-4340199`. The 2024 annual amendment added the clawback policy. The reviewed filings supplied no correction resolving the difference. [FDIC filings index]({PFBC_FDIC_INDEX}) · [FDIC Form 8-K]({PFBC_FDIC_CURRENT_REPORT}) · [FDIC Form 10-K/A]({PFBC_FDIC_AMENDMENT})

The reviewed cases apply to the stated sources and dates and are for personal inspection. Current trading status and financial eligibility require separate checks. Full U.S. coverage remains unverified. [Nasdaq directory]({_SOURCES[0][2]}) · [SEC ticker map]({MAP_URL}) · [SEC exchange map]({EXCHANGE_URL})
"""
