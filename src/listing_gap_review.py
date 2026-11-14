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
FITB_QUARTER = 'https://www.sec.gov/Archives/edgar/data/35527/000003552726000243/fitb-20260930.htm'
FITB_TRANSFER = 'https://www.sec.gov/Archives/edgar/data/35527/000119312526263043/d145237d8a12b.htm'
FITB_NYSE_CERT = 'https://www.sec.gov/Archives/edgar/data/35527/000087666126000519/FITB060926.pdf'
FITB_NASDAQ_REMOVAL = 'https://www.sec.gov/Archives/edgar/data/35527/000119312526267509/d132955d25.htm'
GNL_COVER = 'https://www.sec.gov/Archives/edgar/data/1526113/000110465926123343/tm2628765d1_8k.htm'
GNL_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1526113/000162828026070177/gnl-20260930.htm'
GNL_SERIES_D_E_NYSE = 'https://www.sec.gov/Archives/edgar/data/1526113/000087666123000715/GNLPRDGNLPRE091123.pdf'
GNL_RTL_MERGER = 'https://www.sec.gov/Archives/edgar/data/1526113/000110465923100026/tm2325830d1_8k.htm'
KEY_QUARTER = 'https://www.sec.gov/Archives/edgar/data/91576/000009157626000023/key-20260930.htm'
KEY_COVER = 'https://www.sec.gov/Archives/edgar/data/91576/000119312526443714/d156521d8k.htm'
KEY_SERIES_H_NYSE = 'https://www.sec.gov/Archives/edgar/data/91576/000087666122000709/KEYPRL082522.pdf'
KEY_DIVIDEND_TERMS = 'https://www.sec.gov/Archives/edgar/data/91576/000009157626000020/a3q26earningspresentatio.htm'
MTB_QUARTER = 'https://www.sec.gov/Archives/edgar/data/36270/000003627026000060/mtb-20260930.htm'
MTB_COVER = 'https://www.sec.gov/Archives/edgar/data/36270/000003627026000057/mbt-20261016.htm'
MTB_SERIES_H_NYSE = 'https://www.sec.gov/Archives/edgar/data/36270/000087666122000329/MTBPRH033122.pdf'
MTB_SERIES_J_NYSE = 'https://www.sec.gov/Archives/edgar/data/36270/000087666124000343/MTBPRJ051424.pdf'
MTB_SERIES_K_NYSE = 'https://www.sec.gov/Archives/edgar/data/36270/000087666125000827/MTBPRK110325.pdf'
MTB_SERIES_L_NYSE = 'https://www.sec.gov/Archives/edgar/data/36270/000087666126000638/MTBPRL072326.pdf'
PEB_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1474098/000147409826000072/peb-20260930.htm'
PEB_COVER = 'https://www.sec.gov/Archives/edgar/data/1474098/000147409826000074/peb-20261029.htm'
PEB_SERIES_E_F_NYSE = 'https://www.sec.gov/Archives/edgar/data/1474098/000087666118001270/PEBPRE_PEBPRF8A113018.pdf'
PEB_SERIES_G_NYSE = 'https://www.sec.gov/Archives/edgar/data/1474098/000087666121000716/PEB051221.pdf'
PEB_SERIES_H_NYSE = 'https://www.sec.gov/Archives/edgar/data/1474098/000087666121001123/PEBPRH072721.pdf'
VNO_QUARTER = 'https://www.sec.gov/Archives/edgar/data/899689/000089968926000053/vno-20260930.htm'
VNO_COVER = 'https://www.sec.gov/Archives/edgar/data/899689/000089968926000055/vno-20261102.htm'
VNO_SERIES_L_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/899689/000110465913004808/a13-3025_58a12b.htm'
VNO_SERIES_M_NYSE = 'https://www.sec.gov/Archives/edgar/data/899689/000087666117000755/VNOPRM.8A.12.14.17.pdf'
VNO_SERIES_N_NYSE = 'https://www.sec.gov/Archives/edgar/data/899689/000087666120001105/VNOPRN8A113020.pdf'
VNO_SERIES_O_NYSE = 'https://www.sec.gov/Archives/edgar/data/899689/000087666121001398/VNOPRO092721.pdf'
DLR_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1297996/000110465926120710/dlr-20260930x10q.htm'
DLR_COVER = 'https://www.sec.gov/Archives/edgar/data/1297996/000119312526441892/d170330d8k.htm'
DLR_SERIES_J_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/1297996/000119312517248824/d425847d8a12b.htm'
DLR_SERIES_K_NYSE = 'https://www.sec.gov/Archives/edgar/data/1297996/000087666119000221/DLR8A031219.pdf'
DLR_SERIES_L_NYSE = 'https://www.sec.gov/Archives/edgar/data/1297996/000087666119001034/DLR8A100919.pdf'
EFC_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1411342/000162828026071569/efc-20260930.htm'
EFC_COVER = 'https://www.sec.gov/Archives/edgar/data/1411342/000162828026073150/efc-20261112.htm'
EFC_SERIES_B_NYSE = 'https://www.sec.gov/Archives/edgar/data/1411342/000087666121001738/EFC121321.pdf'
EFC_SERIES_C_NYSE = 'https://www.sec.gov/Archives/edgar/data/1411342/000087666123000092/EFCPRC020623.pdf'
EFC_SERIES_D_E_NYSE = 'https://www.sec.gov/Archives/edgar/data/1411342/000087666123000966/EFCPRDPRE121323.pdf'
KIM_QUARTER = 'https://www.sec.gov/Archives/edgar/data/879101/000119312526437341/kim-20260930.htm'
KIM_COVER = 'https://www.sec.gov/Archives/edgar/data/879101/000119312526436941/kim-20261029.htm'
KIM_SUCCESSION = 'https://www.sec.gov/Archives/edgar/data/879101/000114036123000046/ny20006479x6_8k12b.htm'
KIM_CLASS_N_NYSE = 'https://www.sec.gov/Archives/edgar/data/879101/000087666123001022/KIMPRN122923.pdf'
MET_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1099219/000109921926000062/met-20260930.htm'
MET_COVER = 'https://www.sec.gov/Archives/edgar/data/1099219/000119312526454038/d155870d8k.htm'
MET_SERIES_A_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/1099219/000095012305007232/y09784e8va12b.txt'
MET_SERIES_E_NYSE = 'https://www.sec.gov/Archives/edgar/data/1099219/000087666118000657/METPRE.8A.06.06.18.pdf'
MET_SERIES_F_NYSE = 'https://www.sec.gov/Archives/edgar/data/1099219/000087666120000035/MET8A011620.pdf'
RF_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1281761/000128176126000073/rf-20260930.htm'
RF_COVER = 'https://www.sec.gov/Archives/edgar/data/1281761/000128176126000066/rf-20261104.htm'
RF_SERIES_C_NYSE = 'https://www.sec.gov/Archives/edgar/data/1281761/000087666119000435/RFPRC8A043019.pdf'
RF_SERIES_E_NYSE = 'https://www.sec.gov/Archives/edgar/data/1281761/000087666121000626/RFPRE050321.pdf'
RF_SERIES_F_NYSE = 'https://www.sec.gov/Archives/edgar/data/1281761/000087666124000605/RFPRF072624.pdf'
RF_SERIES_D_ELIMINATION = 'https://www.sec.gov/Archives/edgar/data/1281761/000128176125000053/rf_seriesdcertificateofe.htm'
TFC_QUARTER = 'https://www.sec.gov/Archives/edgar/data/92230/000009223026000129/tfc-20260930.htm'
TFC_COVER = 'https://www.sec.gov/Archives/edgar/data/92230/000119312526423384/d186531d8k.htm'
TFC_SERIES_I_NYSE = 'https://www.sec.gov/Archives/edgar/data/92230/000087666119001227/TFCPRI120619.pdf'
TFC_SERIES_O_NYSE = 'https://www.sec.gov/Archives/edgar/data/92230/000087666120000446/TFCPRO052820.pdf'
TFC_SERIES_R_NYSE = 'https://www.sec.gov/Archives/edgar/data/92230/000087666120000610/TFCPRR080420.pdf'
CFG_QUARTER = 'https://www.sec.gov/Archives/edgar/data/759944/000075994426000213/cfg-20260930.htm'
CFG_COVER = 'https://www.sec.gov/Archives/edgar/data/759944/000119312526441754/d184921d8k.htm'
CFG_SERIES_E_NYSE = 'https://www.sec.gov/Archives/edgar/data/759944/000087666119001068/CFG102519.pdf'
CFG_SERIES_H_NYSE = 'https://www.sec.gov/Archives/edgar/data/759944/000087666124000387/CFGPRH052324.pdf'
CFG_SERIES_I_NYSE = 'https://www.sec.gov/Archives/edgar/data/759944/000087666125000536/CFGPRI073025.pdf'
CFG_SERIES_G_REDEMPTION = 'https://www.sec.gov/Archives/edgar/data/759944/000075994426000192/cfg-20261006.htm'
FHN_QUARTER = 'https://www.sec.gov/Archives/edgar/data/36966/000003696626000199/fhn-20260930.htm'
FHN_COVER = 'https://www.sec.gov/Archives/edgar/data/36966/000003696626000184/fhn-20261026.htm'
FHN_SERIES_E_NYSE = 'https://www.sec.gov/Archives/edgar/data/36966/000087666120000496/FHN8A061120.pdf'
FHN_SERIES_F_NYSE = 'https://www.sec.gov/Archives/edgar/data/36966/000087666121000699/FHNPRF051021.pdf'
FHN_SERIES_H_NYSE = 'https://www.sec.gov/Archives/edgar/data/36966/000087666126000232/FHNPRH031626.pdf'
GS_QUARTER = 'https://www.sec.gov/Archives/edgar/data/886982/000088698226000532/gs-20260930.htm'
GS_COVER = 'https://www.sec.gov/Archives/edgar/data/886982/000119312526460732/d187542d8k.htm'
SCE_QUARTER = 'https://www.sec.gov/Archives/edgar/data/92103/000082705226000073/eix-20260930.htm'
SCE_TRUST_II_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/1122392/000119312513031120/d475965d8a12b.htm'
SCE_TRUST_VI_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/1709317/000009210317000029/scetrustviform8-a.htm'
SCE_TRUST_VII_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/1709318/000009210323000027/tmb-20231122x8a12b.htm'
SCE_TRUST_VIII_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/92103/000009210324000023/tmb-20240514x8a12b.htm'
SCE_SERIES_K_REMOVAL = 'https://www.sec.gov/Archives/edgar/data/876661/000087666126000238/primary_doc.xml'
PMT_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1464423/000119312526445330/pmt-20260930.htm'
PMT_COVER = 'https://www.sec.gov/Archives/edgar/data/1464423/000119312526437878/d179622d8k.htm'
EPR_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1045450/000104545026000051/epr-20260930.htm'
EPR_COVER = 'https://www.sec.gov/Archives/edgar/data/1045450/000119312526456657/d488669d8k.htm'
EPR_Q3_SUPPLEMENT = 'https://www.sec.gov/Archives/edgar/data/1045450/000104545026000050/ex993-eprx9302026supplemen.htm'
SF_QUARTER = 'https://www.sec.gov/Archives/edgar/data/720672/000119312526446268/sf-20260930.htm'
SF_COVER = 'https://www.sec.gov/Archives/edgar/data/720672/000119312526427189/d182962d8k.htm'
SF_DIVIDENDS = 'https://www.stifel.com/docs/pdf/pressreleases/2026/SF-4Q26-Dividend-Announcement.pdf'
SF_SERIES_A_REMOVAL = 'https://www.sec.gov/Archives/edgar/data/876661/000087666121001211/primary_doc.xml'
SF_SERIES_D_REGISTRATION = 'https://www.sec.gov/Archives/edgar/data/720672/000119312521221582/d46382d8a12b.htm'
SF_SERIES_D_DESIGNATION = 'https://www.sec.gov/Archives/edgar/data/720672/000119312521221582/d46382dex998.htm'
MITT_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1514281/000162828026071791/mitt-20260930.htm'
MITT_COVER = 'https://www.sec.gov/Archives/edgar/data/1514281/000162828026069770/mitt-20261104.htm'
MITT_NAME_AMENDMENT = 'https://www.sec.gov/Archives/edgar/data/1514281/000162828025057427/a8k-121625xexhibit31.htm'
CMRE_ANNUAL = 'https://www.sec.gov/Archives/edgar/data/1503584/000114036126007868/ef20064083_20f.htm'
CMRE_DIVIDENDS = 'https://www.sec.gov/Archives/edgar/data/1503584/000117184326006324/exh_991.htm'
CMRE_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1503584/000117184326006884/exh_991.htm'
CODI_QUARTER = 'https://www.sec.gov/Archives/edgar/data/1345126/000134512626000071/codi-20260930.htm'
CODI_COVER = 'https://www.sec.gov/Archives/edgar/data/1345126/000134512626000072/codi-20261104.htm'
CODI_DISTRIBUTIONS = 'https://www.sec.gov/Archives/edgar/data/1345126/000134512626000065/codidistributionpressrelea.htm'
PNFP_QUARTER = 'https://www.sec.gov/Archives/edgar/data/2082866/000208286626000092/pnfp-20260930.htm'
PNFP_COVER = 'https://www.sec.gov/Archives/edgar/data/2082866/000208286626000094/pnfp-20261104.htm'
PNFP_MERGER = 'https://www.sec.gov/Archives/edgar/data/2082866/000114036126000050/ef20061822_8k12b.htm'
PNFP_NYSE_CERT = 'https://www.sec.gov/Archives/edgar/data/2082866/000087666125001026/PNFP123125.pdf'
GAB_COVER = 'https://www.sec.gov/Archives/edgar/data/794685/000182912626004782/gab_8k.htm'
GAB_SEMIANNUAL = 'https://www.sec.gov/Archives/edgar/data/794685/000182912626009842/gab_ncsrs.htm'
GAB_PROSPECTUS = 'https://www.sec.gov/Archives/edgar/data/794685/000182912626003035/gabelliequitytrust_424b4.htm'
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

- **544 SEC-only records.** These rows carry an exchange in the SEC map and lack a confirmed symbol join to either directory. 192 were reviewed, with 352 still unreviewed.
- **282 unresolved directory types.** 246 had no recognized instrument wording, 19 had ambiguous wording, and 17 had conflicting flag and description evidence. Fifteen now have dated class evidence, with 267 still unreviewed.

**Dated findings**

- **Gabelli Equity Trust · Three NYSE preferred share listings matched.** The May 7 Form 8-K identifies Series G, H and K, and the semiannual shareholder report records all three as 5.00% fixed cumulative preferred stock as of June 30. Each row gives the SEC map, filing cover and November 12 Nasdaq Trader directory symbols. The same-day NYSE report shows trading activity in all three. [Gabelli Form 8-K]({GAB_COVER}) · [Semiannual shareholder report]({GAB_SEMIANNUAL}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=71)
  - `GAB-PG` / `GAB Pr G` / `GAB$G` · Series G
  - `GAB-PH` / `GAB Pr H` / `GAB$H` · Series H
  - `GAB-PK` / `GAB Pr K` / `GAB$K` · Series K
  - The filings resolve the directory-type gap for `GAB$H`, abbreviated `Pfd Ser H` in the directory. Series M and Q are off-exchange, and the separate auction-rate Series C and E were redeemed in 2024. [April prospectus supplement]({GAB_PROSPECTUS})
- **Pinnacle Financial Partners · Three NYSE preferred security listings matched.** The November 2 Form 10-Q and November 4 Form 8-K identify three series of noncumulative perpetual preferred stock, with Series C listed through depositary shares. Each row gives the SEC map, filing cover and November 12 Nasdaq Trader directory symbols. The same-day NYSE report shows activity in all three. [Pinnacle Form 10-Q]({PNFP_QUARTER}) · [Pinnacle Form 8-K]({PNFP_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=137)
  - `PNFP-PA` / `PNFP - PrA` / `PNFP$A` · Series A · fixed-to-floating preferred stock
  - `PNFP-PB` / `PNFP - PrB` / `PNFP$B` · Series B · fixed-rate reset preferred stock
  - `PNFP-PC` / `PNFP - PrC` / `PNFP$C` · Series C · depositary shares, each representing 1/40 of a 6.75% fixed-rate preferred share
  - The directory describes both B and C as fixed-to-floating stock. The SEC filings and NYSE certification establish the classes shown here. [December 31 NYSE certification]({PNFP_NYSE_CERT})
  - In the January 1, 2026 merger, Synovus Series D and E became Series A and B of the new Pinnacle. Legacy Pinnacle's `PNFPP` depositary shares converted into the new Series C depositary shares. [January 2 merger filing]({PNFP_MERGER})
- **Compass Diversified Holdings · Three NYSE preferred share listings matched.** The November 4 Form 10-Q and Form 8-K identify the preferred shares as beneficial interests in the trust. Compass Group Diversified Holdings LLC is a separate co-registrant. Each row gives the SEC map, filing cover and November 12 Nasdaq Trader directory symbols. The same-day NYSE report shows activity in all three classes. [Compass Form 10-Q]({CODI_QUARTER}) · [Compass Form 8-K]({CODI_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=39)
  - `CODI-PA` / `CODI PR A` / `CODI$A` · Series A · 7.250% fixed, noncumulative
  - `CODI-PB` / `CODI PR B` / `CODI$B` · Series B · 7.875% fixed-to-floating, cumulative
  - `CODI-PC` / `CODI PR C` / `CODI$C` · Series C · 7.875% fixed, cumulative
  - Series B is scheduled to switch to a floating rate on April 30, 2028. Preferred distributions were declared for payment on October 30, 2026. The common shares are outside this batch. [October 1 distribution declaration]({CODI_DISTRIBUTIONS})
- **Costamare · Three NYSE preferred share listings matched.** The March 4 Form 20-F lists Series B, C and D. The October 1 dividend declaration identifies each as cumulative redeemable perpetual preferred stock, and the October 28 results confirm the October 15 payments. Each row lists the SEC map, annual filing cover, issuer and November 12 Nasdaq Trader directory symbols. The same-day NYSE report shows activity in each class. [Costamare Form 20-F]({CMRE_ANNUAL}) · [October 1 dividend declaration]({CMRE_DIVIDENDS}) · [October 28 results]({CMRE_QUARTER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=38)
  - `CMRE-PB` / `CMRE.PRB` / `CMRE PR B` / `CMRE$B` · Series B · 7.625%
  - `CMRE-PC` / `CMRE.PRC` / `CMRE PR C` / `CMRE$C` · Series C · 8.50%
  - `CMRE-PD` / `CMRE.PRD` / `CMRE PR D` / `CMRE$D` · Series D · 8.75%
  - Series E was fully redeemed on July 15, 2024. Series F sits outside the listed preferred classes. Costamare Bulkers (`CMDB`) is a separate issuer.
- **TPG Mortgage Investment Trust · Three NYSE preferred share listings matched.** The November 6 Form 10-Q and November 4 Form 8-K identify all three classes as cumulative redeemable preferred stock. Each row lists the SEC map, SEC cover and November 12 Nasdaq Trader directory symbols. The same-day NYSE report shows activity in each class. [TPG Mortgage Form 10-Q]({MITT_QUARTER}) · [TPG Mortgage Form 8-K]({MITT_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=112)
  - `MITT-PA` / `MITT PrA` / `MITT$A` · Series A · 8.25% fixed
  - `MITT-PB` / `MITT PrB` / `MITT$B` · Series B · 8.00% fixed
  - `MITT-PC` / `MITT PrC` / `MITT$C` · Series C · 8.000% original fixed rate, now floating
  - Series C has used a floating rate based on three-month CME Term SOFR since September 17, 2024. `MITN` and `MITP` are separate senior notes.
  - The same issuer changed its legal name from AG Mortgage Investment Trust, Inc. on December 16, 2025. [Charter amendment]({MITT_NAME_AMENDMENT})
- **Stifel Financial · Three NYSE depositary share listings matched.** The November 4 Form 10-Q and October 21 Form 8-K identify three listings. Each depositary share represents 1/1,000 of a non-cumulative perpetual preferred share. Each row gives the SEC map and cover symbol, the trading symbol from Stifel's November 2 announcement, and the November 12 directory symbol. The same-day NYSE report corroborates activity. [Stifel Form 10-Q]({SF_QUARTER}) · [Stifel Form 8-K]({SF_COVER}) · [Stifel dividend declaration]({SF_DIVIDENDS}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=155)
  - `SF-PB` / `SF PrB` / `SF$B` · Series B · 6.25%
  - `SF-PC` / `SF PrC` / `SF$C` · Series C · 6.125%
  - `SF-PD` / `SF PrD` / `SF$D` · Series D · 4.50%
  - Item 1 of the Series D Form 8-A says Series C once. Its registration table, designation and later SEC covers identify the 4.50% security as Series D. Stifel could redeem Series D from August 15, 2026, subject to regulatory approval, and reported it outstanding at September 30. [Series D Form 8-A]({SF_SERIES_D_REGISTRATION}) · [Series D designation]({SF_SERIES_D_DESIGNATION})
  - Series A was redeemed on August 20, 2021. `SFB` is the 5.20% senior notes listing. Both fall outside this batch. [NYSE Series A Form 25]({SF_SERIES_A_REMOVAL})
- **EPR Properties · Three NYSE preferred share listings matched.** The October 29 Form 10-Q and November 12 Form 8-K identify all three classes. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the stated class terms. [EPR Form 10-Q]({EPR_QUARTER}) · [EPR Form 8-K]({EPR_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=57)
  - `EPR-PC` / `EPR PrC` / `EPR$C` · Series C · 5.75% cumulative convertible
  - `EPR-PE` / `EPR PrE` / `EPR$E` · Series E · 9.00% cumulative convertible
  - `EPR-PG` / `EPR PrG` / `EPR$G` · Series G · 5.75% cumulative redeemable
  - The filings resolve the directory-type gap for `EPR$E`. As of September 30, 2026, EPR reported conversion ratios of 0.4433 for Series C and 0.4866 for Series E, in common shares per preferred share. [EPR quarterly supplement]({EPR_Q3_SUPPLEMENT})
  - The 4.5% convertible senior notes fall outside this batch.
- **PennyMac Mortgage Investment Trust · Three NYSE preferred share listings matched.** The November 3 Form 10-Q and October 29 Form 8-K identify the cumulative redeemable preferred shares of beneficial interest. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, 10-Q cover, 8-K cover and directory symbols, followed by the stated class rate. [PennyMac Form 10-Q]({PMT_QUARTER}) · [PennyMac Form 8-K]({PMT_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=137)
  - `PMT-PA` / `PMT/PRA` / `PMT/PA` / `PMT$A` · Series A · 8.125%
  - `PMT-PB` / `PMT/PRB` / `PMT/PB` / `PMT$B` · Series B · 8.00%
  - `PMT-PC` / `PMT/PRC` / `PMT/PC` / `PMT$C` · Series C · 6.75%
  - PennyMac reports that Series A and B retained their prior dividend rates under its reading of the LIBOR fallback. The dispute remains pending as reported in the 10-Q.
  - Series A, B and C became optionally redeemable on March 15, 2024, June 15, 2024 and August 24, 2026, respectively. The filing reports that no preferred shares were redeemed through September 30, 2026. `PMTU`, `PMTV` and `PMTW` are senior notes and fall outside this batch.
- **Southern California Edison · Four NYSE trust preference securities matched.** The trusts issue the listed securities. SCE is the guarantor and issues the underlying preference stock. The October 29 joint Form 10-Q reports no Section 12(b) securities for SCE on its cover. The trust registrations, November 12 Nasdaq Trader directory and same-day NYSE report support the matches below. Each row gives the SEC map, NYSE and directory symbols, followed by the underlying series, trust issuer and stated rate. [Joint Form 10-Q]({SCE_QUARTER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=153)
  - `SCE-PG` / `SCE PR G` / `SCE$G` · Series G · SCE Trust II · 5.10%
  - `SCE-PL` / `SCE PR L` / `SCE$L` · Series L · SCE Trust VI · 5.00%
  - `SCE-PM` / `SCE PR M` / `SCE$M` · Series M · SCE Trust VII · 7.50%
  - `SCE-PN` / `SCE PR N` / `SCE$N` · Series N · SCE Trust VIII · 6.95%
  - The filings resolve the directory-type gaps for `SCE$L`, `SCE$M` and `SCE$N`. See the Forms 8-A for [Trust II]({SCE_TRUST_II_REGISTRATION}), [Trust VI]({SCE_TRUST_VI_REGISTRATION}), [Trust VII]({SCE_TRUST_VII_REGISTRATION}) and [Trust VIII]({SCE_TRUST_VIII_REGISTRATION}).
  - Trust V Series K was redeemed in March 2026 and falls outside this batch. [NYSE Form 25 for the Series K guarantee]({SCE_SERIES_K_REMOVAL})
- **Goldman Sachs · Three NYSE depositary share listings matched.** The November 2 Form 10-Q and November 13 Form 8-K identify the three listings. Each depositary share represents 1/1,000 of a floating-rate non-cumulative preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols. [Goldman Sachs Form 10-Q]({GS_QUARTER}) · [Goldman Sachs Form 8-K]({GS_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=78)
  - `GS-PA` / `GS PrA` / `GS$A` · Series A
  - `GS-PC` / `GS PrC` / `GS$C` · Series C
  - `GS-PD` / `GS PrD` / `GS$D` · Series D
  - The filings also resolve the directory-type gap for `GS$D`.
  - Series O and V were fully redeemed on November 10 and fall outside this batch.
  - The separate NYSE trust capital securities and medium-term notes fall outside this batch.
- **First Horizon · Three NYSE depositary share listings matched.** The November 5 Form 10-Q and October 27 Form 8-K identify the three listings. Each depositary share represents 1/4,000 of its underlying preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the stated class rate. [First Horizon Form 10-Q]({FHN_QUARTER}) · [First Horizon Form 8-K]({FHN_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=64)
  - `FHN-PE` / `FHN PR E` / `FHN$E` · Series E · 6.500%
  - `FHN-PF` / `FHN PR F` / `FHN$F` · Series F · 4.700%
  - `FHN-PH` / `FHN PR H` / `FHN$H` · Series H · 6.750%
  - Series H was issued on March 12, 2026. Series C was fully redeemed on May 1, 2026 and falls outside this batch. NYSE certifications for [Series E]({FHN_SERIES_E_NYSE}), [Series F]({FHN_SERIES_F_NYSE}) and [Series H]({FHN_SERIES_H_NYSE}).
- **Citizens Financial Group · Three NYSE depositary share listings matched.** The October 28 Form 10-Q and October 30 Form 8-K identify the three listings. Each depositary share represents 1/40 of its underlying preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the rate terms. [Citizens Form 10-Q]({CFG_QUARTER}) · [Citizens Form 8-K]({CFG_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report, Series E]({NOV12_NYSE_VOLUME}#page=33) · [November 12 NYSE report, Series H and I]({NOV12_NYSE_VOLUME}#page=34)
  - `CFG-PE` / `CFG PrE` / `CFG$E` · Series E · 5.000% fixed
  - `CFG-PH` / `CFG PrH` / `CFG$H` · Series H · 7.375% fixed
  - `CFG-PI` / `CFG PrI` / `CFG$I` · Series I · 6.500% fixed-rate reset
  - Series I's first scheduled reset is October 6, 2030. Series G was fully redeemed on October 6, 2026. The separate Series J issuance falls outside this batch. NYSE certifications for [Series E]({CFG_SERIES_E_NYSE}), [Series H]({CFG_SERIES_H_NYSE}) and [Series I]({CFG_SERIES_I_NYSE}) · [Series G Form 8-K]({CFG_SERIES_G_REDEMPTION}).
- **Truist Financial · Three NYSE depositary share listings matched.** The October 28 Form 10-Q and October 16 Form 8-K identify all three listings. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the fraction of an underlying preferred share. [Truist Form 10-Q]({TFC_QUARTER}) · [Truist Form 8-K]({TFC_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=170)
  - `TFC-PI` / `TFC.PI` / `TFC$I` · Series I · 1/4,000
  - `TFC-PO` / `TFC.PO` / `TFC$O` · Series O · 1/1,000
  - `TFC-PR` / `TFC.PR` / `TFC$R` · Series R · 1/1,000
  - The SEC covers identify Series I behind the directory’s generic depositary share description. `TFC.PJ` is a separate Series J preferred purchase security outside this SEC-only batch. NYSE certifications for [Series I]({TFC_SERIES_I_NYSE}), [Series O]({TFC_SERIES_O_NYSE}) and [Series R]({TFC_SERIES_R_NYSE}).
- **Regions Financial · Three NYSE depositary share listings matched.** The November 9 Form 10-Q and November 4 Form 8-K identify the three listings. Each depositary share represents 1/40 of its underlying preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the rate terms. [Regions Form 10-Q]({RF_QUARTER}) · [Regions Form 8-K]({RF_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=146)
  - `RF-PC` / `RF PRC` / `RF$C` · Series C · 5.700% fixed-to-floating
  - `RF-PE` / `RF PRE` / `RF$E` · Series E · 4.450% fixed
  - `RF-PF` / `RF PRF` / `RF$F` · Series F · 6.950% fixed-rate reset
  - Series C is scheduled to switch to a floating rate on August 15, 2029. Series F is scheduled for its first fixed-rate reset on September 15, 2029. Series D was fully redeemed in the second quarter of 2025 and falls outside this batch. NYSE certifications for [Series C]({RF_SERIES_C_NYSE}), [Series E]({RF_SERIES_E_NYSE}) and [Series F]({RF_SERIES_F_NYSE}) · [Series D certificate of elimination]({RF_SERIES_D_ELIMINATION}).
- **MetLife · Three NYSE preferred-linked listings matched.** The November 6 Form 10-Q and November 10 Form 8-K identify one direct preferred stock listing and two depositary share listings. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols. [MetLife Form 10-Q]({MET_QUARTER}) · [MetLife Form 8-K]({MET_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=110)
  - `MET-PA` / `MET PRA` / `MET$A` · Series A · Direct floating-rate preferred stock
  - `MET-PE` / `MET PRE` / `MET$E` · Series E · 5.625% · Depositary share · 1/1,000
  - `MET-PF` / `MET PRF` / `MET$F` · Series F · 4.75% · Depositary share · 1/1,000
  - The SEC covers identify Series E behind the directory’s generic depositary share description. Series A Junior Participating Preferred Stock and Series D fall outside this batch. [Series A Form 8-A]({MET_SERIES_A_REGISTRATION}) · NYSE certifications for [Series E]({MET_SERIES_E_NYSE}) and [Series F]({MET_SERIES_F_NYSE}).
- **Kimco Realty · Three NYSE depositary share listings matched.** The October 29 Form 10-Q and Form 8-K identify three listings of Kimco Realty Corporation. Each listed depositary share represents 1/1,000 of its underlying preferred share. Kimco Realty OP, LLC is a separate registrant. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the stated class rate. [Kimco Form 10-Q]({KIM_QUARTER}) · [Kimco Form 8-K]({KIM_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=100)
  - `KIM-PL` / `KIMprL` / `KIM$L` · Class L · 5.125%
  - `KIM-PM` / `KIMprM` / `KIM$M` · Class M · 5.250%
  - `KIM-PN` / `KIMprN` / `KIM$N` · Class N · 7.250%
  - Classes L and M are cumulative redeemable preferred stock. Class N is convertible perpetual preferred stock with cumulative dividends. The Form 10-Q shows all three classes outstanding on September 30 after partial repurchases. [Class L and M succession filing]({KIM_SUCCESSION}) · [NYSE Class N certification]({KIM_CLASS_N_NYSE})
- **Ellington Financial · Three NYSE preferred share listings matched.** The November 6 Form 10-Q and November 12 Form 8-K identify three direct cumulative redeemable preferred share classes. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the stated class rate. [Ellington Form 10-Q]({EFC_QUARTER}) · [Ellington Form 8-K]({EFC_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=54)
  - `EFC-PB` / `EFC PR B` / `EFC$B` · Series B · 6.250% fixed-rate reset
  - `EFC-PC` / `EFC PR C` / `EFC$C` · Series C · 8.625% fixed-rate reset
  - `EFC-PD` / `EFC PRD` / `EFC$D` · Series D · 7.000% fixed
  - The Form 10-Q gives the first scheduled reset dates as January 30, 2027 for Series B and April 30, 2028 for Series C. Series A was fully redeemed on February 27, 2026 and falls outside this batch. [NYSE Series B certification]({EFC_SERIES_B_NYSE}) · [NYSE Series C certification]({EFC_SERIES_C_NYSE}) · [NYSE Series D and E certification]({EFC_SERIES_D_E_NYSE})
- **Digital Realty Trust · Three NYSE preferred share listings matched.** The October 30 Form 10-Q and Form 8-K identify the three direct cumulative redeemable preferred stock listings of Digital Realty Trust, Inc. Digital Realty Trust, L.P. preferred units fall outside this batch. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, SEC cover and directory symbols, followed by the stated class rate. [Digital Realty Form 10-Q]({DLR_QUARTER}) · [Digital Realty Form 8-K]({DLR_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=49)
  - `DLR-PJ` / `DLR Pr J` / `DLR$J` · Series J · 5.250%
  - `DLR-PK` / `DLR Pr K` / `DLR$K` · Series K · 5.850%
  - `DLR-PL` / `DLR Pr L` / `DLR$L` · Series L · 5.200%
  - The Form 10-Q reports dividends for all three stock classes through September 30. The historical registration records document the class terms. [Series J Form 8-A]({DLR_SERIES_J_REGISTRATION}) · NYSE certifications for [Series K]({DLR_SERIES_K_NYSE}) and [Series L]({DLR_SERIES_L_NYSE}).
- **Vornado Realty Trust · Four NYSE preferred share listings matched.** The November 2 joint Form 10-Q and Form 8-K identify four direct cumulative redeemable preferred shares of beneficial interest. The cover assigns all four listings to the Trust. Vornado Realty L.P. units fall outside this batch. Each row gives the SEC map, SEC cover and directory symbols, followed by the stated class rate. [Vornado Form 10-Q]({VNO_QUARTER}) · [Vornado Form 8-K]({VNO_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=184)
  - `VNO-PL` / `VNO/PL` / `VNO$L` · Series L · 5.40%
  - `VNO-PM` / `VNO/PM` / `VNO$M` · Series M · 5.25%
  - `VNO-PN` / `VNO/PN` / `VNO$N` · Series N · 5.25%
  - `VNO-PO` / `VNO/PO` / `VNO$O` · Series O · 4.45%
  - The directory abbreviates Series L as `Pfd Ser L %`. The filings provide dated preferred share evidence for this row. In the saved snapshot, the original directory classification remains unknown. [Series L Form 8-A]({VNO_SERIES_L_REGISTRATION}) · NYSE certifications for [Series M]({VNO_SERIES_M_NYSE}), [Series N]({VNO_SERIES_N_NYSE}) and [Series O]({VNO_SERIES_O_NYSE}).
- **Pebblebrook Hotel Trust · Four NYSE preferred share listings matched.** The October 29 Form 10-Q and Form 8-K identify four direct cumulative redeemable preferred shares of beneficial interest. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the shared SEC map and cover symbol, the directory symbol and the stated class rate. [Pebblebrook Form 10-Q]({PEB_QUARTER}) · [Pebblebrook Form 8-K]({PEB_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=133)
  - `PEB-PE` / `PEB$E` · Series E · 6.375%
  - `PEB-PF` / `PEB$F` · Series F · 6.30%
  - `PEB-PG` / `PEB$G` · Series G · 6.375%
  - `PEB-PH` / `PEB$H` · Series H · 5.70%
  - The Form 10-Q shows all four series outstanding on September 30 after partial repurchases. Series Z operating partnership units fall outside this batch. NYSE certifications document the class terms for [Series E and F]({PEB_SERIES_E_F_NYSE}), [Series G]({PEB_SERIES_G_NYSE}) and [Series H]({PEB_SERIES_H_NYSE}).
- **M&T Bank · Four NYSE preferred-linked listings matched.** The November 5 Form 10-Q and October 16 Form 8-K identify all four NYSE listings. The original NYSE certifications distinguish direct Series H stock from the Series J, K and L depositary shares. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, filing cover and directory symbols. [M&T Bank Form 10-Q]({MTB_QUARTER}) · [M&T Bank Form 8-K]({MTB_COVER}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=116)
  - `MTB-PH` / `MTBPrH` / `MTB$H` · Series H · Direct preferred stock
  - `MTB-PJ` / `MTBPrJ` / `MTB$J` · Series J · Depositary share · 1/400
  - `MTB-PK` / `MTBPrK` / `MTB$K` · Series K · Depositary share · 1/400
  - `MTB-PL` / `MTBPrL` / `MTB$L` · Series L · Depositary share · 1/400
  - Each depositary share represents 1/400 of its underlying preferred share. Series F was fully redeemed on November 1, 2026 and falls outside this batch. NYSE certifications for [Series H]({MTB_SERIES_H_NYSE}), [Series J]({MTB_SERIES_J_NYSE}), [Series K]({MTB_SERIES_K_NYSE}) and [Series L]({MTB_SERIES_L_NYSE}) support the class distinctions.
- **KeyCorp · Four NYSE depositary share listings matched.** The November 3 Form 10-Q and November 2 Form 8-K identify the four classes. These depositary shares each represent 1/40 of one preferred share. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, filing cover and directory symbols. [KeyCorp Form 10-Q]({KEY_QUARTER}) · [KeyCorp Form 8-K]({KEY_COVER}) · [NYSE Series H certification]({KEY_SERIES_H_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=100)
  - `KEY-PI` / `KEY PrI` / `KEY$I` · Series E
  - `KEY-PJ` / `KEY PrJ` / `KEY$J` · Series F
  - `KEY-PK` / `KEY PrK` / `KEY$K` · Series G
  - `KEY-PL` / `KEY PrL` / `KEY$L` · Series H
  - The directory omits the reset feature for Series H. The SEC cover and NYSE certification identify it as fixed-rate reset. KeyCorp’s October 20 exhibit gives December 15, 2026 for the Series E floating-rate transition and December 15, 2027 for the first Series H reset. [KeyCorp preferred dividend terms]({KEY_DIVIDEND_TERMS})
  - Series D’s 1/25 depositary shares were redeemed on September 15, 2026 and fall outside this batch.
- **Global Net Lease · Four NYSE preferred share listings matched.** The November 5 Form 8-K and November 4 Form 10-Q identify four direct cumulative redeemable preferred stock classes. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, filing cover and directory symbols, followed by the series and stated class rate. [Global Net Lease Form 8-K]({GNL_COVER}) · [Global Net Lease Form 10-Q]({GNL_QUARTER}) · [NYSE Series D and E certification]({GNL_SERIES_D_E_NYSE}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=76)
  - `GNL-PA` / `GNL PR A` / `GNL$A` · Series A · 7.25%
  - `GNL-PB` / `GNL PR B` / `GNL$B` · Series B · 6.875%
  - `GNL-PD` / `GNL PR D` / `GNL$D` · Series D · 7.50%
  - `GNL-PE` / `GNL PR E` / `GNL$E` · Series E · 7.375%
  - Series D and E succeeded The Necessity Retail REIT’s Series A and C, respectively, in the September 12, 2023 merger. [Merger closing Form 8-K]({GNL_RTL_MERGER})
- **Fifth Third · Four NYSE depositary share listings matched.** The November 3 Form 10-Q lists all four on NYSE. The June 9 Form 8-A and NYSE certification document the transfer from Nasdaq. The November 12 Nasdaq Trader directory and same-day NYSE report corroborate the matches. Each row gives the SEC map, filing cover and directory symbols, followed by the underlying series and share fraction. [Fifth Third Form 10-Q]({FITB_QUARTER}) · [Transfer Form 8-A]({FITB_TRANSFER}) · [NYSE certification]({FITB_NYSE_CERT}) · [Nasdaq Trader directory]({_SOURCES[1][2]}) · [November 12 NYSE report]({NOV12_NYSE_VOLUME}#page=65)
  - `FITB-PA` / `FITB PrA` / `FITB$A` · Series A · 1/40
  - `FITB-PI` / `FITB PrI` / `FITB$I` · Series I · 1/1,000
  - `FITB-PK` / `FITB PrK` / `FITB$K` · Series K · 1/1,000
  - `FITB-PM` / `FITB PrM` / `FITB$M` · Series M · 1/40
  - The June 11 Form 25 covers withdrawal from Nasdaq. Series M succeeded Comerica’s Series B in the February merger. The separate NYSE Texas registration applies to the common stock. [Nasdaq withdrawal Form 25]({FITB_NASDAQ_REMOVAL})
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
