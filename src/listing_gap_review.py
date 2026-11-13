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
JPM_COVER = 'https://www.sec.gov/Archives/edgar/data/19617/000162828026069523/jpm-20260930.htm'
JPM_SERIES_MM_NYSE = 'https://www.sec.gov/Archives/edgar/data/19617/000087666121001134/JPMPRM072921.pdf'
MS_COVER = 'https://www.sec.gov/Archives/edgar/data/895421/000089542126000293/ms-20260930.htm'
MS_SECURITIES = 'https://www.sec.gov/Archives/edgar/data/895421/000089542126000086/exhibit41q42025_10k.htm'
NOV12_NYSE_VOLUME = 'https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf'
BAC_COVER = 'https://www.sec.gov/Archives/edgar/data/70858/000007085826000548/bac-20260930.htm'
BAC_OCT23_COVER = 'https://www.sec.gov/Archives/edgar/data/70858/000119312526430566/d176604d8k.htm'
BAC_SERIES_SS_NYSE = 'https://www.sec.gov/Archives/edgar/data/70858/000087666122000107/BACPRS013122.pdf'
USB_COVER = 'https://www.sec.gov/Archives/edgar/data/36104/000119312526450781/d172862d8k.htm'
USB_QUARTER = 'https://www.sec.gov/Archives/edgar/data/36104/000003610426000058/usb-20260930.htm'
USB_SERIES_P_TERMS = 'https://www.sec.gov/Archives/edgar/data/36104/000119312526441737/d20659dex43.htm'
PSA_COVER = 'https://www.sec.gov/Archives/edgar/data/1393311/000119312526456624/d158518d8k.htm'
PSA_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1393311/000162828026067286/psa-20260930.htm'
PSA_SERIES_T_U_NYSE = 'https://www.sec.gov/Archives/edgar/data/1393311/000087666126000633/PSAPRTPRU.pdf'
PCG_UTILITY_COVER = 'https://www.sec.gov/Archives/edgar/data/75488/000199937126024070/pcg-8k_102926.htm'
PCG_JOINT_QUARTER = 'https://www.sec.gov/Archives/edgar/data/75488/000100498026000055/pcg-20260930.htm'
NOV12_NYSE_AMERICAN_VOLUME = 'https://ftp.nyse.com/ShortData/Amexshvol/Amexshvol2026/Amexshvol202611/Amexshvol20261112.pdf'
WFC_QUARTER = 'https://www.sec.gov/Archives/edgar/data/72971/000007297126000327/wfc-20260930.htm'
WFC_COVER = 'https://www.sec.gov/Archives/edgar/data/72971/000007297126000318/wfc-20261013.htm'
WFC_SERIES_DD_NYSE = 'https://www.sec.gov/Archives/edgar/data/72971/000087666121001124/WFCPRD072921.pdf'
WFC_SERIES_HH = 'https://www.sec.gov/Archives/edgar/data/72971/000119312526356890/d144651d8k.htm'
AHT_EARNINGS_COVER = 'https://www.sec.gov/Archives/edgar/data/1232582/000123258226000214/aht-20261110.htm'
AHT_OFFICER_COVER = 'https://www.sec.gov/Archives/edgar/data/1232582/000110465926125247/tm2629394d1_8k.htm'
AHT_EARNINGS_EXHIBIT = 'https://www.sec.gov/Archives/edgar/data/1232582/000123258226000214/aht2026q3earningsrelease.htm'
COF_COVER = 'https://www.sec.gov/Archives/edgar/data/927628/000092762826000157/cof-20261110.htm'
COF_QUARTER = 'https://www.sec.gov/Archives/edgar/data/927628/000092762826000152/cof-20260930.htm'
COF_SERIES_N_NYSE = 'https://www.sec.gov/Archives/edgar/data/927628/000087666121001133/COFPRN072921.pdf'
COF_SERIES_M = 'https://www.sec.gov/Archives/edgar/data/927628/000119312526378455/d477310d8k.htm'
ALL_QUARTER = 'https://www.sec.gov/Archives/edgar/data/899051/000089905126000157/all-20260930.htm'
ALL_COVER = 'https://www.sec.gov/Archives/edgar/data/899051/000089905126000156/all-20261104.htm'
ALL_SERIES_J_NYSE = 'https://www.sec.gov/Archives/edgar/data/899051/000087666123000432/ALLPRJ052423.pdf'
ALL_DEBT_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/899051/000110465913001880/a13-2630_18a12b.htm'
ATH_COVER = 'https://www.sec.gov/Archives/edgar/data/1527469/000152746926000090/ahl-20261112.htm'
ATH_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1527469/000152746926000085/ahl-20260930.htm'
ATH_SERIES_E_NYSE = 'https://www.sec.gov/Archives/edgar/data/1527469/000087666122001120/ATHPRE121322.pdf'
ATH_SECURITIES = 'https://www.sec.gov/Archives/edgar/data/1527469/000152746926000013/q42025exhibit48.htm'
ATH_SERIES_C = 'https://www.sec.gov/Archives/edgar/data/1527469/000119312525154072/d948326d8k.htm'
CIM_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1409493/000140949326000068/cim-20260930.htm'
CIM_DIVIDEND_COVER = 'https://www.sec.gov/Archives/edgar/data/1409493/000120677426000594/cim4711711-8k.htm'
CIM_DIVIDEND_EXHIBIT = 'https://www.sec.gov/Archives/edgar/data/1409493/000120677426000594/cim4711711-ex991.htm'
CIM_SERIES_D_NYSE = 'https://www.sec.gov/Archives/edgar/data/1409493/000087666119000039/CIM8A012219.pdf'
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

- **544 SEC-only records.** These rows carry an exchange in the SEC map and lack a confirmed symbol join to either directory. 113 were reviewed, with 431 still unreviewed.
- **282 unresolved directory types.** 246 had no recognized instrument wording, 19 had ambiguous wording, and 17 had conflicting flag and description evidence. Eight now have dated class evidence, with 274 still unreviewed.

**Dated findings**

- **Chimera Investment · Four NYSE preferred share listings matched.** The November 5 Forms 10-Q and 8-K identify four direct cumulative redeemable preferred stock classes. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, filing cover and directory symbols. [Chimera Form 10-Q]({CIM_QUARTER}) · [Preferred dividends Form 8-K]({CIM_DIVIDEND_COVER}) · [NYSE Series D certification]({CIM_SERIES_D_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=36)
  - `CIM-PA` / `CIM PRA` / `CIM$A` · Series A
  - `CIM-PB` / `CIM PRB` / `CIM$B` · Series B
  - `CIM-PC` / `CIM PRC` / `CIM$C` · Series C
  - `CIM-PD` / `CIM PRD` / `CIM$D` · Series D
  - Series B, C and D use floating rates. The percentages in their class titles identify the original fixed rates. Chimera reported fourth-quarter 2026 annualized dividend rates of 10.14841%, 9.10041% and 9.73641%, respectively, in its November 5 declaration. [Preferred dividends exhibit]({CIM_DIVIDEND_EXHIBIT})
- **Athene · Four NYSE depositary share listings matched.** The November 12 Form 8-K and November 5 Form 10-Q identify the four classes. These depositary shares each represent 1/1,000 of one preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, filing cover and directory symbols. [Athene Form 8-K]({ATH_COVER}) · [Athene Form 10-Q]({ATH_QUARTER}) · [NYSE Series E certification]({ATH_SERIES_E_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=14)
  - `ATH-PA` / `ATHPrA` / `ATH$A` · Series A
  - `ATH-PB` / `ATHPrB` / `ATH$B` · Series B
  - `ATH-PD` / `ATHPrD` / `ATH$D` · Series D
  - `ATH-PE` / `ATHPrE` / `ATH$E` · Series E
  - Series A’s 6.35% fixed period ends before June 30, 2029. Series E’s first reset date is December 30, 2027. These are filed terms. [Athene securities description]({ATH_SECURITIES})
  - Series C was fully redeemed on June 30, 2025 and falls outside this batch. [Series C redemption Form 8-K]({ATH_SERIES_C})
- **Allstate · Three NYSE depositary share listings matched.** The November 4 Forms 10-Q and 8-K identify Series H, I and J. Each depositary share represents 1/1,000 of one preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the dated matches. Each row gives the SEC map, filing cover and directory symbols. [Allstate Form 10-Q]({ALL_QUARTER}) · [Allstate Form 8-K]({ALL_COVER}) · [NYSE Series J certification]({ALL_SERIES_J_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=8)
  - `ALL-PH` / `ALL PR H` / `ALL$H` · Series H
  - `ALL-PI` / `ALL PR I` / `ALL$I` · Series I
  - `ALL-PJ` / `ALL PR J` / `ALL$J` · Series J
- **Allstate · One NYSE debt listing identified.** `ALL-PB` / `ALL.PR.B` / `ALL$B` · 5.100% fixed-to-floating rate subordinated debentures due 2053. This record is included in the SEC-only review total and excluded from the preferred-share count. [Debentures Form 8-A]({ALL_DEBT_REGISTRATION})
- **Capital One · Five NYSE depositary share listings matched.** The November 10 Form 8-K and November 3 Form 10-Q identify the five classes. These depositary shares each represent 1/40 of one preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the dated matches. Each row gives the SEC map, filing cover and directory symbols. [Capital One Form 8-K]({COF_COVER}) · [Capital One Form 10-Q]({COF_QUARTER}) · [NYSE Series N certification]({COF_SERIES_N_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=39)
  - `COF-PI` / `COF PRI` / `COF$I` · Series I
  - `COF-PJ` / `COF PRJ` / `COF$J` · Series J
  - `COF-PK` / `COF PRK` / `COF$K` · Series K
  - `COF-PL` / `COF PRL` / `COF$L` · Series L
  - `COF-PN` / `COF PRN` / `COF$N` · Series N
  - Series M was fully redeemed on September 1. Series O uses a 1/100 depositary interest. Both fall outside this batch. [Series M Form 8-K]({COF_SERIES_M})
- **Ashford Hospitality Trust · Five NYSE preferred share listings matched.** Two November 10 Forms 8-K list the same five direct cumulative preferred share classes. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map and filing symbol followed by the directory symbol and stated class rate. [Earnings Form 8-K]({AHT_EARNINGS_COVER}) · [Officer change Form 8-K]({AHT_OFFICER_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=6)
  - `AHT-PD` / `AHT$D` · Series D · 8.45%
  - `AHT-PF` / `AHT$F` · Series F · 7.375%
  - `AHT-PG` / `AHT$G` · Series G · 7.375%
  - `AHT-PH` / `AHT$H` · Series H · 7.50%
  - `AHT-PI` / `AHT$I` · Series I · 7.50%
  - On November 10, Ashford reported that preferred dividends remained suspended and continued to accumulate. Series J, K, L and M and the preferred stock purchase rights fall outside this batch. [September-quarter earnings exhibit]({AHT_EARNINGS_EXHIBIT})
- **Wells Fargo · Six NYSE preferred-linked listings matched.** The October 28 Form 10-Q, October 13 Form 8-K and November 12 exchange records support these matches. Five depositary shares each represent 1/1,000 of one preferred share. Series L is listed as direct convertible preferred stock. Each row gives the SEC map, filing cover and directory symbols. [Wells Fargo Form 10-Q]({WFC_QUARTER}) · [Wells Fargo Form 8-K]({WFC_COVER}) · [NYSE Series DD certification]({WFC_SERIES_DD_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=188)
  - `WFC-PA` / `WFC.PRA` / `WFC$A` · Series AA
  - `WFC-PC` / `WFC.PRC` / `WFC$C` · Series CC
  - `WFC-PD` / `WFC.PRD` / `WFC$D` · Series DD
  - `WFC-PL` / `WFC.PRL` / `WFC$L` · Series L · Direct convertible preferred stock
  - `WFC-PY` / `WFC.PRY` / `WFC$Y` · Series Y
  - `WFC-PZ` / `WFC.PRZ` / `WFC$Z` · Series Z
  - The separate Series HH offering represents a 1/25 interest per depositary share and falls outside this batch. [Series HH Form 8-K]({WFC_SERIES_HH})
- **Pacific Gas and Electric Company · Eight NYSE American preferred share listings matched.** The November 2 utility Form 8-K and October 22 joint Form 10-Q list all eight as direct cumulative first preferred shares with $25 par value. The SEC exchange map labels all eight NYSE. The filing covers and November 12 Nasdaq Trader directory identify NYSE American, and the same-day NYSE American report shows activity for all eight. Each row gives the SEC map and filing symbol followed by the directory symbol. [Utility Form 8-K]({PCG_UTILITY_COVER}) · [Joint Form 10-Q]({PCG_JOINT_QUARTER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE American report]({NOV12_NYSE_AMERICAN_VOLUME}#page=102)
  - `PCG-PA` / `PCG$A` · 6% nonredeemable
  - `PCG-PB` / `PCG$B` · 5.50% nonredeemable
  - `PCG-PC` / `PCG$C` · 5% nonredeemable
  - `PCG-PD` / `PCG$D` · 5% redeemable
  - `PCG-PE` / `PCG$E` · 5% Series A redeemable
  - `PCG-PG` / `PCG$G` · 4.80% redeemable
  - `PCG-PH` / `PCG$H` · 4.50% redeemable
  - `PCG-PI` / `PCG$I` · 4.36% redeemable
  - PG&E Corporation’s separate `PCG-PrX` mandatory convertible preferred share appears on NYSE in the joint filing and falls outside this batch.
- **Public Storage · Sixteen NYSE preferred-linked listings matched.** The Form 8-K filed November 12, September-quarter Form 10-Q and November 12 exchange records support the matches. Series F through S are depositary shares, each representing 1/1,000 of one preferred share. Series T and U are direct preferred shares covered by the July 21 NYSE certification. Each row gives the SEC map, filing cover and directory symbols. [Public Storage Form 8-K]({PSA_COVER}) · [Public Storage Form 10-Q]({PSA_QUARTER}) · [NYSE Series T and U certification]({PSA_SERIES_T_U_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report, F–R]({NOV12_NYSE_VOLUME}#page=139) · [November 12 NYSE report, S–U]({NOV12_NYSE_VOLUME}#page=140)
  - `PSA-PF` / `PSAPrF` / `PSA$F` · Series F
  - `PSA-PG` / `PSAPrG` / `PSA$G` · Series G
  - `PSA-PH` / `PSAPrH` / `PSA$H` · Series H
  - `PSA-PI` / `PSAPrI` / `PSA$I` · Series I
  - `PSA-PJ` / `PSAPrJ` / `PSA$J` · Series J
  - `PSA-PK` / `PSAPrK` / `PSA$K` · Series K
  - `PSA-PL` / `PSAPrL` / `PSA$L` · Series L
  - `PSA-PM` / `PSAPrM` / `PSA$M` · Series M
  - `PSA-PN` / `PSAPrN` / `PSA$N` · Series N
  - `PSA-PO` / `PSAPrO` / `PSA$O` · Series O
  - `PSA-PP` / `PSAPrP` / `PSA$P` · Series P
  - `PSA-PQ` / `PSAPrQ` / `PSA$Q` · Series Q
  - `PSA-PR` / `PSAPrR` / `PSA$R` · Series R
  - `PSA-PS` / `PSAPrS` / `PSA$S` · Series S
  - `PSA-PT` / `PSAPrT` / `PSA$T` · Series T · Direct preferred shares
  - `PSA-PU` / `PSAPrU` / `PSA$U` · Series U · Direct preferred shares
- **U.S. Bancorp · Six NYSE depositary share listings matched.** The November 6 Form 8-K and November 5 Form 10-Q identify the underlying preferred shares. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the dated matches. Each row gives the SEC map, filing cover and directory symbols, followed by the underlying series and share fraction. [U.S. Bancorp Form 8-K]({USB_COVER}) · [U.S. Bancorp Form 10-Q]({USB_QUARTER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=179)
  - `USB-PA` / `USB PrA` / `USB$A` · Series A · 1/100
  - `USB-PH` / `USB PrH` / `USB$H` · Series B · 1/1,000
  - `USB-PP` / `USB PrP` / `USB$P` · Series K · 1/1,000
  - `USB-PQ` / `USB PrQ` / `USB$Q` · Series L · 1/1,000
  - `USB-PR` / `USB PrR` / `USB$R` · Series M · 1/1,000
  - `USB-PS` / `USB PrS` / `USB$S` · Series O · 1/1,000
  - `USB-PP` represents Series K. The separate Series P offering represents a 1/25 interest and falls outside this batch. [Series P deposit agreement]({USB_SERIES_P_TERMS})
- **Bank of America · Ten NYSE preferred-linked listings matched.** The October 30 Form 10-Q, November 12 Nasdaq Trader directory and same-day NYSE report support these matches. Nine depositary shares each represent 1/1,000 of one preferred share. Series L is listed as direct convertible preferred stock. Each row gives the SEC map, filing cover and directory symbols. [Bank of America Form 10-Q]({BAC_COVER}) · [NYSE Series SS certification]({BAC_SERIES_SS_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=18)
  - `BAC-PB` / `BAC PrB` / `BAC$B` · Series GG
  - `BAC-PE` / `BAC PrE` / `BAC$E` · Series E
  - `BAC-PK` / `BAC PrK` / `BAC$K` · Series HH
  - `BAC-PL` / `BAC PrL` / `BAC$L` · Series L · Direct convertible preferred stock
  - `BAC-PM` / `BAC PrM` / `BAC$M` · Series KK
  - `BAC-PN` / `BAC PrN` / `BAC$N` · Series LL
  - `BAC-PO` / `BAC PrO` / `BAC$O` · Series NN
  - `BAC-PP` / `BAC PrP` / `BAC$P` · Series PP
  - `BAC-PQ` / `BAC PrQ` / `BAC$Q` · Series QQ
  - `BAC-PS` / `BAC PrS` / `BAC$S` · Series SS
  - The original description rule still leaves the abbreviated `BAC$E` and `BAC$L` unknown. The four `BML`-prefixed listings are reviewed separately below.
- **Bank of America BML · Four NYSE depositary share listings matched.** Each represents 1/1,200 of a share of Bank of America floating-rate non-cumulative preferred stock. The October 30 Form 10-Q, October 23 Form 8-K and November 12 exchange records support the matches. Each row gives the SEC map, filing cover and directory symbols. [Bank of America Form 10-Q]({BAC_COVER}) · [Bank of America Form 8-K]({BAC_OCT23_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=24)
  - `BML-PG` / `BML PrG` / `BML$G` · Series 1
  - `BML-PH` / `BML PrH` / `BML$H` · Series 2
  - `BML-PJ` / `BML PrJ` / `BML$J` · Series 4
  - `BML-PL` / `BML PrL` / `BML$L` · Series 5
  - `BML-PL` represents Series 5. `BAC-PL` is direct Series L convertible preferred stock.
- **Morgan Stanley · Nine NYSE depositary share listings matched.** The November 5 Form 10-Q lists each depositary share as a 1/1,000 interest in the named preferred series. The November 12 Nasdaq Trader directory and NYSE short-sale volume report corroborate the dated symbol matches. Each row gives the SEC map, filing cover and directory symbols in that order. [Morgan Stanley Form 10-Q]({MS_COVER}) · [SEC securities description]({MS_SECURITIES}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME})
  - `MS-PA` / `MS/PA` / `MS$A` · Series A
  - `MS-PE` / `MS/PE` / `MS$E` · Series E
  - `MS-PF` / `MS/PF` / `MS$F` · Series F
  - `MS-PI` / `MS/PI` / `MS$I` · Series I
  - `MS-PK` / `MS/PK` / `MS$K` · Series K
  - `MS-PL` / `MS/PL` / `MS$L` · Series L
  - `MS-PO` / `MS/PO` / `MS$O` · Series O
  - `MS-PP` / `MS/PP` / `MS$P` · Series P
  - `MS-PQ` / `MS/PQ` / `MS$Q` · Series Q
  - The original description rule leaves the abbreviated `MS$A` and `MS$F` rows unknown. The `MS$I` directory description says `Series 1`. The SEC filings identify Series I, and the NYSE report uses `MS PRI` with the letter I. The source wording remains visible.
- **JPMorgan Chase · Six NYSE depositary share listings matched.** The November 3 Form 10-Q and November 12 Nasdaq Trader directory identify each listed depositary share as a 1/400 interest in one underlying preferred share. Each line gives the SEC map, filing cover and directory symbols, followed by the underlying series. [JPMorgan Form 10-Q]({JPM_COVER}) · [NYSE Series MM certification]({JPM_SERIES_MM_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]})
  - `JPM-PC` / `JPM PR C` / `JPM$C` · Series EE
  - `JPM-PD` / `JPM PR D` / `JPM$D` · Series DD
  - `JPM-PJ` / `JPM PR J` / `JPM$J` · Series GG
  - `JPM-PK` / `JPM PR K` / `JPM$K` · Series JJ
  - `JPM-PL` / `JPM PR L` / `JPM$L` · Series LL
  - `JPM-PM` / `JPM PR M` / `JPM$M` · Series MM
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
