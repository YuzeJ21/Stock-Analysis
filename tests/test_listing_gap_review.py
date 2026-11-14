def test_dated_listing_gap_review_preserves_both_populations_and_the_original_inventory():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert '2026-11-12' in review and '13,791' in review and '38 test issues excluded' in review
    assert '544 SEC-only' in review and '282 unresolved directory types' in review
    assert '246' in review and '19' in review and '17' in review
    assert '202 were reviewed, with 342 still unreviewed' in review
    assert 'Fifteen now have dated class evidence, with 267 still unreviewed' in review
    assert all(symbol in review for symbol in ('ABR-PD', 'ABR-PE', 'ABR-PF', 'ALUR', 'GOOG', 'ADSEW', 'PFBC'))
    assert 'Form 25' in review and 'Class C Capital Stock' in review and 'Nasdaq warrant' in review
    assert 'Full U.S. coverage remains unverified' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1253986/000125398626000064/abr-20261030.htm' in review


def test_farmer_mac_review_uses_exact_series_and_symbol_spellings():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Six NYSE preferred share classes matched' in review
    assert all(f'AGM-P{series}' in review and f'AGM.PR{series}' in review and f'AGM${series}' in review
               for series in 'DEFGHI')
    assert 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000143/agm-20261112.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/845877/000084587726000139/agm-20260930.htm' in review


def test_triton_review_keeps_the_seven_distinct_preference_share_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Seven NYSE preference share classes matched' in review
    for series in 'ABCDEFG':
        assert f'TRTN-P{series}' in review and f'TRTN PR{series}' in review and f'TRTN${series}' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1660734/000166073426000005/trtn-20251231.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1660734/000162828026071407/trtn-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1660734/000087666126000041/TRTNPRG011326.pdf' in review


def test_rithm_review_keeps_six_distinct_preferred_classes_and_rate_scope():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Rithm Capital Series A–F · Six NYSE preferred share classes matched' in review
    for series in 'ABCDEF':
        assert f'`RITM-P{series}`' in review and f'`RITM PR {series}`' in review and f'`RITM${series}`' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1556593/000155659326000035/nrz-20260930.htm' in review
    assert 'class titles' in review and 'Current yields are outside this review' in review


def test_annaly_review_distinguishes_short_directory_title_and_redeemed_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Annaly Series F, G and J · Three NYSE preferred share classes matched' in review
    for series in 'FGJ':
        assert f'`NLY-P{series}`' in review and f'`NLY.{series}`' in review and f'`NLY${series}`' in review
    assert '`NLYPrF` as the NYSE listing symbol' in review and "CQS spelling is `NLYpF`" in review
    assert 'description rule still leaves `NLY$F` unknown' in review
    assert 'Series I was redeemed October 1' in review and 'excluded from the reviewed counts' in review
    assert 'October 12 opening' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1043219/000104321926000083/nly-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1043219/000119312517235069/d417558dfwp.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/876661/000087666126000807/ruleprovisionnotice.htm' in review


def test_pfbc_common_stock_is_dated_to_the_fdic_covers():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'PFBC · Nasdaq common stock confirmed as filed' in review
    assert 'November 9' in review and 'September 30' in review and '33539' in review
    assert 'PFBC · Type remains unresolved' not in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/12041/attachment/1' in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11872/attachment/1' in review


def test_jpm_review_matches_listed_depositary_shares_to_underlying_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'JPMorgan Chase · Six NYSE depositary share listings matched' in review
    assert '1/400' in review
    for suffix, series in zip('CDJKLM', ('EE', 'DD', 'GG', 'JJ', 'LL', 'MM')):
        assert f'`JPM-P{suffix}` / `JPM PR {suffix}` / `JPM${suffix}` · Series {series}' in review
    assert 'https://www.sec.gov/Archives/edgar/data/19617/000162828026069523/jpm-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/19617/000087666121001134/JPMPRM072921.pdf' in review


def test_pfbc_filing_patterns_keep_the_irs_number_unreconciled():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'PFBC IRS number · Unreconciled' in review
    assert 'Six quarterly covers from 2025 and 2026 show `95-4340119`' in review
    assert 'October 27 Form 8-K show `95-4340199`' in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/11687/attachment/1' in review
    assert 'https://securitiesfilings.fdicconnect.fdic.gov/api/instflng/cert/33539' in review


def test_morgan_stanley_review_matches_depositary_shares_and_retains_directory_discrepancy():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Morgan Stanley · Nine NYSE depositary share listings matched' in review
    assert '1/1,000' in review and 'November 5 Form 10-Q' in review
    for series in 'AEFIKLOPQ':
        assert f'`MS-P{series}` / `MS/P{series}` / `MS${series}`' in review
    assert '`Series 1`' in review and '`MS PRI`' in review
    assert '`MS$A` and `MS$F`' in review and 'original description rule' in review
    assert 'https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf' in review


def test_bank_of_america_review_distinguishes_direct_preferred_and_depositary_shares():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Bank of America · Ten NYSE preferred-linked listings matched' in review
    assert 'Nine depositary shares each represent 1/1,000' in review
    for suffix, series in zip('BEKLMNOPQS', ('GG', 'E', 'HH', 'L', 'KK', 'LL', 'NN', 'PP', 'QQ', 'SS')):
        assert f'`BAC-P{suffix}` / `BAC Pr{suffix}` / `BAC${suffix}` · Series {series}' in review
    assert 'Series L · Direct convertible preferred stock' in review
    assert '`BAC$E` and `BAC$L` unknown' in review
    assert 'The four `BML`-prefixed listings are reviewed separately below' in review
    assert 'https://www.sec.gov/Archives/edgar/data/70858/000007085826000548/bac-20260930.htm' in review


def test_bml_review_maps_four_depositary_symbols_to_numbered_preferred_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Bank of America BML · Four NYSE depositary share listings matched' in review
    assert '1/1,200 of a share of Bank of America floating-rate non-cumulative preferred stock' in review
    for suffix, series in zip('GHJL', '1245'):
        assert f'`BML-P{suffix}` / `BML Pr{suffix}` / `BML${suffix}` · Series {series}' in review
    assert '`BML-PL` represents Series 5' in review and '`BAC-PL` is direct Series L' in review
    assert 'https://www.sec.gov/Archives/edgar/data/70858/000119312526430566/d176604d8k.htm' in review
    assert 'https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=24' in review


def test_us_bancorp_review_matches_depositary_ratios_and_distinguishes_series_p():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'U.S. Bancorp · Six NYSE depositary share listings matched' in review
    for suffix, series in zip('AHPQRS', 'ABKLMO', strict=True):
        ratio = '1/100' if suffix == 'A' else '1/1,000'
        assert f'`USB-P{suffix}` / `USB Pr{suffix}` / `USB${suffix}` · Series {series} · {ratio}\n' in review
    assert '`USB-PP` represents Series K' in review and 'separate Series P offering' in review
    assert 'https://www.sec.gov/Archives/edgar/data/36104/000003610426000058/usb-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/36104/000119312526450781/d172862d8k.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/36104/000119312526441737/d20659dex43.htm' in review
    assert 'https://ftp.nyse.com/ShortData/NYSEshvol/NYSEshvol2026/NYSEshvol202611/NYSEshvol20261112.pdf#page=179' in review


def test_public_storage_review_distinguishes_depositary_and_direct_preferred_shares():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Public Storage · Sixteen NYSE preferred-linked listings matched' in review
    assert 'Series F through S are depositary shares' in review and '1/1,000' in review
    for series in 'FGHIJKLMNOPQRSTU':
        instrument = ' · Direct preferred shares' if series in 'TU' else ''
        assert f'`PSA-P{series}` / `PSAPr{series}` / `PSA${series}` · Series {series}{instrument}\n' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1393311/000119312526456624/d158518d8k.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1393311/000162828026067286/psa-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1393311/000087666126000633/PSAPRTPRU.pdf' in review
    for page in (139, 140):
        assert f'NYSEshvol20261112.pdf#page={page}' in review


def test_pacific_gas_and_electric_review_preserves_the_venue_conflict_and_issuer():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Pacific Gas and Electric Company · Eight NYSE American preferred share listings matched' in review
    assert 'The SEC exchange map labels all eight NYSE' in review
    assert 'PG&E Corporation’s separate `PCG-PrX`' in review
    terms = (
        ('A', '6% nonredeemable'), ('B', '5.50% nonredeemable'), ('C', '5% nonredeemable'),
        ('D', '5% redeemable'), ('E', '5% Series A redeemable'), ('G', '4.80% redeemable'),
        ('H', '4.50% redeemable'), ('I', '4.36% redeemable'),
    )
    for suffix, title in terms:
        assert f'`PCG-P{suffix}` / `PCG${suffix}` · {title}\n' in review
    assert 'https://www.sec.gov/Archives/edgar/data/75488/000199937126024070/pcg-8k_102926.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/75488/000100498026000055/pcg-20260930.htm' in review
    assert 'Amexshvol20261112.pdf#page=102' in review


def test_wells_fargo_review_keeps_series_l_and_the_separate_hh_offering_distinct():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Wells Fargo · Six NYSE preferred-linked listings matched' in review
    assert 'Five depositary shares each represent 1/1,000' in review
    for suffix, series in zip('ACDLYZ', ('AA', 'CC', 'DD', 'L', 'Y', 'Z'), strict=True):
        instrument = ' · Direct convertible preferred stock' if suffix == 'L' else ''
        assert f'`WFC-P{suffix}` / `WFC.PR{suffix}` / `WFC${suffix}` · Series {series}{instrument}\n' in review
    assert 'separate Series HH offering represents a 1/25 interest' in review
    assert 'https://www.sec.gov/Archives/edgar/data/72971/000007297126000327/wfc-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/72971/000007297126000318/wfc-20261013.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/72971/000087666121001124/WFCPRD072921.pdf' in review
    assert 'https://www.sec.gov/Archives/edgar/data/72971/000119312526356890/d144651d8k.htm' in review
    assert 'NYSEshvol20261112.pdf#page=188' in review


def test_ashford_review_separates_class_rates_from_suspended_dividends():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Ashford Hospitality Trust · Five NYSE preferred share listings matched' in review
    for suffix, rate in zip('DFGHI', ('8.45%', '7.375%', '7.375%', '7.50%', '7.50%'), strict=True):
        assert f'`AHT-P{suffix}` / `AHT${suffix}` · Series {suffix} · {rate}\n' in review
    assert 'preferred dividends remained suspended and continued to accumulate' in review
    assert 'Series J, K, L and M and the preferred stock purchase rights fall outside this batch' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1232582/000123258226000214/aht-20261110.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1232582/000110465926125247/tm2629394d1_8k.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1232582/000123258226000214/aht2026q3earningsrelease.htm' in review
    assert 'NYSEshvol20261112.pdf#page=6' in review


def test_capital_one_review_matches_exact_classes_and_preserves_separate_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Capital One · Five NYSE depositary share listings matched' in review
    assert 'each represent 1/40 of one preferred share' in review
    for series in 'IJKLN':
        assert f'`COF-P{series}` / `COF PR{series}` / `COF${series}` · Series {series}\n' in review
    assert 'Series M was fully redeemed on September 1' in review
    assert 'Series O uses a 1/100 depositary interest' in review
    assert 'https://www.sec.gov/Archives/edgar/data/927628/000092762826000157/cof-20261110.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/927628/000092762826000152/cof-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/927628/000087666121001133/COFPRN072921.pdf' in review
    assert 'https://www.sec.gov/Archives/edgar/data/927628/000119312526378455/d477310d8k.htm' in review
    assert 'NYSEshvol20261112.pdf#page=39' in review


def test_allstate_review_keeps_subordinated_debt_out_of_the_preferred_count():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Allstate · Three NYSE depositary share listings matched' in review
    assert 'Allstate · One NYSE debt listing identified' in review
    for series in 'HIJ':
        assert f'`ALL-P{series}` / `ALL PR {series}` / `ALL${series}` · Series {series}\n' in review
    assert '`ALL-PB` / `ALL.PR.B` / `ALL$B` · 5.100% fixed-to-floating rate subordinated debentures due 2053' in review
    assert 'excluded from the preferred-share count' in review
    assert 'https://www.sec.gov/Archives/edgar/data/899051/000089905126000157/all-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/899051/000089905126000156/all-20261104.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/899051/000087666123000432/ALLPRJ052423.pdf' in review
    assert 'https://www.sec.gov/Archives/edgar/data/899051/000110465913001880/a13-2630_18a12b.htm' in review
    assert 'NYSEshvol20261112.pdf#page=8' in review


def test_athene_review_matches_four_depositary_classes_and_excludes_redeemed_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Athene · Four NYSE depositary share listings matched' in review
    assert 'each represent 1/1,000 of one preferred share' in review
    for series in 'ABDE':
        assert f'`ATH-P{series}` / `ATHPr{series}` / `ATH${series}` · Series {series}\n' in review
    assert 'Series A’s 6.35% fixed period ends before June 30, 2029' in review
    assert 'Series E’s first reset date is December 30, 2027' in review
    assert 'Series C was fully redeemed on June 30, 2025' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1527469/000152746926000090/ahl-20261112.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1527469/000152746926000085/ahl-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1527469/000087666122001120/ATHPRE121322.pdf' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1527469/000152746926000013/q42025exhibit48.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1527469/000119312525154072/d948326d8k.htm' in review
    assert 'NYSEshvol20261112.pdf#page=14' in review


def test_chimera_review_distinguishes_class_titles_from_floating_dividend_rates():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Chimera Investment · Four NYSE preferred share listings matched' in review
    assert 'four direct cumulative redeemable preferred stock classes' in review
    for series in 'ABCD':
        assert f'`CIM-P{series}` / `CIM PR{series}` / `CIM${series}` · Series {series}\n' in review
    assert 'Series B, C and D use floating rates' in review
    assert 'percentages in their class titles identify the original fixed rates' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1409493/000140949326000068/cim-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1409493/000120677426000594/cim4711711-8k.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1409493/000120677426000594/cim4711711-ex991.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1409493/000087666119000039/CIM8A012219.pdf' in review
    assert 'NYSEshvol20261112.pdf#page=36' in review


def test_fifth_third_review_keeps_share_fractions_and_exchange_transfer_distinct():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Fifth Third · Four NYSE depositary share listings matched' in review
    for series, fraction in zip('AIKM', ('1/40', '1/1,000', '1/1,000', '1/40'), strict=True):
        assert f'`FITB-P{series}` / `FITB Pr{series}` / `FITB${series}` · Series {series} · {fraction}\n' in review
    assert 'June 11 Form 25 covers withdrawal from Nasdaq' in review
    assert 'Series M succeeded Comerica’s Series B' in review
    assert 'NYSE Texas registration applies to the common stock' in review
    assert 'https://www.sec.gov/Archives/edgar/data/35527/000003552726000243/fitb-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/35527/000119312526263043/d145237d8a12b.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/35527/000087666126000519/FITB060926.pdf' in review
    assert 'https://www.sec.gov/Archives/edgar/data/35527/000119312526267509/d132955d25.htm' in review
    assert 'NYSEshvol20261112.pdf#page=65' in review


def test_global_net_lease_review_matches_four_direct_classes_and_their_lineage():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'Global Net Lease · Four NYSE preferred share listings matched' in review
    for series, rate in zip('ABDE', ('7.25%', '6.875%', '7.50%', '7.375%'), strict=True):
        assert f'`GNL-P{series}` / `GNL PR {series}` / `GNL${series}` · Series {series} · {rate}\n' in review
    assert 'Series D and E succeeded The Necessity Retail REIT’s Series A and C, respectively' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1526113/000110465926123343/tm2628765d1_8k.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1526113/000162828026070177/gnl-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1526113/000087666123000715/GNLPRDGNLPRE091123.pdf' in review
    assert 'https://www.sec.gov/Archives/edgar/data/1526113/000110465923100026/tm2325830d1_8k.htm' in review
    assert 'NYSEshvol20261112.pdf#page=76' in review


def test_keycorp_review_keeps_filing_series_reset_terms_and_redemption_distinct():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert 'KeyCorp · Four NYSE depositary share listings matched' in review
    assert 'each represent 1/40 of one preferred share' in review
    for suffix, series in zip('IJKL', 'EFGH', strict=True):
        assert f'`KEY-P{suffix}` / `KEY Pr{suffix}` / `KEY${suffix}` · Series {series}\n' in review
    assert 'The directory omits the reset feature for Series H' in review
    assert 'Series D’s 1/25 depositary shares were redeemed on September 15, 2026' in review
    assert 'https://www.sec.gov/Archives/edgar/data/91576/000009157626000023/key-20260930.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/91576/000119312526443714/d156521d8k.htm' in review
    assert 'https://www.sec.gov/Archives/edgar/data/91576/000087666122000709/KEYPRL082522.pdf' in review
    assert 'https://www.sec.gov/Archives/edgar/data/91576/000009157626000020/a3q26earningspresentatio.htm' in review
    assert 'NYSEshvol20261112.pdf#page=100' in review


def test_mt_bank_review_distinguishes_direct_preferred_and_depositary_shares():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    batch = review.split('**M&T Bank · Four NYSE preferred-linked listings matched.**', 1)[1]
    batch = batch.split('\n- **', 1)[0]
    assert '`MTB-PH` / `MTBPrH` / `MTB$H` · Series H · Direct preferred stock\n' in batch
    for series in 'JKL':
        assert f'`MTB-P{series}` / `MTBPr{series}` / `MTB${series}` · Series {series} · Depositary share · 1/400\n' in batch
    assert 'Series F was fully redeemed on November 1, 2026' in batch
    assert '`MTB-PF`' not in batch
    assert '000003627026000060/mtb-20260930.htm' in batch
    assert '000003627026000057/mbt-20261016.htm' in batch
    for certification in ('MTBPRH033122.pdf', 'MTBPRJ051424.pdf', 'MTBPRK110325.pdf', 'MTBPRL072326.pdf'):
        assert certification in batch
    assert 'NYSEshvol20261112.pdf#page=116' in batch


def test_pebblebrook_review_distinguishes_listed_shares_from_partnership_units():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Pebblebrook Hotel Trust · Four NYSE preferred share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('EFGH', ('6.375%', '6.30%', '6.375%', '5.70%'), strict=True):
        assert f'`PEB-P{series}` / `PEB${series}` · Series {series} · {rate}\n' in batch
    assert 'all four series outstanding on September 30' in batch
    assert 'Series Z operating partnership units fall outside this batch' in batch
    assert '000147409826000072/peb-20260930.htm' in batch
    assert '000147409826000074/peb-20261029.htm' in batch
    for certification in ('PEBPRE_PEBPRF8A113018.pdf', 'PEB051221.pdf', 'PEBPRH072721.pdf'):
        assert certification in batch
    assert 'NYSEshvol20261112.pdf#page=133' in batch


def test_vornado_review_resolves_one_directory_type_and_keeps_registrants_distinct():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Vornado Realty Trust · Four NYSE preferred share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('LMNO', ('5.40%', '5.25%', '5.25%', '4.45%'), strict=True):
        assert f'`VNO-P{series}` / `VNO/P{series}` / `VNO${series}` · Series {series} · {rate}\n' in batch
    assert 'The cover assigns all four listings to the Trust' in batch
    assert 'Vornado Realty L.P. units fall outside this batch' in batch
    assert 'Pfd Ser L %' in batch and 'the original directory classification remains unknown' in batch
    assert '000089968926000053/vno-20260930.htm' in batch
    assert '000089968926000055/vno-20261102.htm' in batch
    assert '000110465913004808/a13-3025_58a12b.htm' in batch
    assert 'NYSEshvol20261112.pdf#page=184' in batch


def test_digital_realty_review_links_stock_listings_and_excludes_partnership_units():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Digital Realty Trust · Three NYSE preferred share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('JKL', ('5.250%', '5.850%', '5.200%'), strict=True):
        assert f'`DLR-P{series}` / `DLR Pr {series}` / `DLR${series}` · Series {series} · {rate}\n' in batch
    assert 'Digital Realty Trust, L.P. preferred units fall outside this batch' in batch
    assert '000110465926120710/dlr-20260930x10q.htm' in batch
    assert '000119312526441892/d170330d8k.htm' in batch
    assert '000119312517248824/d425847d8a12b.htm' in batch
    assert 'DLR8A031219.pdf' in batch
    assert 'DLR8A100919.pdf' in batch
    assert 'NYSEshvol20261112.pdf#page=49' in batch


def test_ellington_review_preserves_exact_aliases_and_reset_terms():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Ellington Financial · Three NYSE preferred share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    assert '`EFC-PB` / `EFC PR B` / `EFC$B` · Series B · 6.250% fixed-rate reset\n' in batch
    assert '`EFC-PC` / `EFC PR C` / `EFC$C` · Series C · 8.625% fixed-rate reset\n' in batch
    assert '`EFC-PD` / `EFC PRD` / `EFC$D` · Series D · 7.000% fixed\n' in batch
    assert 'January 30, 2027' in batch and 'April 30, 2028' in batch
    assert 'Series A was fully redeemed on February 27, 2026' in batch
    assert '000162828026071569/efc-20260930.htm' in batch
    assert '000162828026073150/efc-20261112.htm' in batch
    for certification in ('EFC121321.pdf', 'EFCPRC020623.pdf', 'EFCPRDPRE121323.pdf'):
        assert certification in batch
    assert 'NYSEshvol20261112.pdf#page=54' in batch


def test_kimco_review_keeps_depositary_listings_and_underlying_classes_distinct():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Kimco Realty · Three NYSE depositary share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for cls, rate in zip('LMN', ('5.125%', '5.250%', '7.250%'), strict=True):
        assert f'`KIM-P{cls}` / `KIMpr{cls}` / `KIM${cls}` · Class {cls} · {rate}\n' in batch
    assert '1/1,000 of its underlying preferred share' in batch
    assert 'Class N is convertible perpetual preferred stock' in batch
    assert 'Kimco Realty OP, LLC is a separate registrant' in batch
    assert 'all three classes outstanding on September 30 after partial repurchases' in batch
    assert '000119312526437341/kim-20260930.htm' in batch
    assert '000119312526436941/kim-20261029.htm' in batch
    assert '000114036123000046/ny20006479x6_8k12b.htm' in batch
    assert 'KIMPRN122923.pdf' in batch and 'NYSEshvol20261112.pdf#page=100' in batch


def test_metlife_review_distinguishes_direct_floating_and_depositary_listings():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**MetLife · Three NYSE preferred-linked listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    assert '`MET-PA` / `MET PRA` / `MET$A` · Series A · Direct floating-rate preferred stock\n' in batch
    for series, rate in zip('EF', ('5.625%', '4.75%'), strict=True):
        assert f'`MET-P{series}` / `MET PR{series}` / `MET${series}` · Series {series} · {rate} · Depositary share · 1/1,000\n' in batch
    assert 'Series A Junior Participating Preferred Stock and Series D fall outside this batch' in batch
    assert '000109921926000062/met-20260930.htm' in batch
    assert '000119312526454038/d155870d8k.htm' in batch
    assert '000095012305007232/y09784e8va12b.txt' in batch
    assert 'METPRE.8A.06.06.18.pdf' in batch and 'MET8A011620.pdf' in batch
    assert 'NYSEshvol20261112.pdf#page=110' in batch


def test_regions_review_preserves_depositary_mappings_and_distinct_rate_terms():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Regions Financial · Three NYSE depositary share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, terms in zip('CEF', ('5.700% fixed-to-floating', '4.450% fixed', '6.950% fixed-rate reset'), strict=True):
        assert f'`RF-P{series}` / `RF PR{series}` / `RF${series}` · Series {series} · {terms}\n' in batch
    assert '1/40 of its underlying preferred share' in batch
    assert 'August 15, 2029' in batch and 'September 15, 2029' in batch
    assert 'Series D was fully redeemed in the second quarter of 2025' in batch
    assert 'rf_seriesdcertificateofe.htm' in batch
    assert '000128176126000073/rf-20260930.htm' in batch
    assert '000128176126000066/rf-20261104.htm' in batch
    for certification in ('RFPRC8A043019.pdf', 'RFPRE050321.pdf', 'RFPRF072624.pdf'):
        assert certification in batch
    assert 'NYSEshvol20261112.pdf#page=146' in batch


def test_truist_review_preserves_depositary_fractions_and_series_j_scope():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Truist Financial · Three NYSE depositary share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, fraction in zip('IOR', ('1/4,000', '1/1,000', '1/1,000'), strict=True):
        assert f'`TFC-P{series}` / `TFC.P{series}` / `TFC${series}` · Series {series} · {fraction}\n' in batch
    assert '`TFC.PJ` is a separate Series J preferred purchase security' in batch
    assert 'outside this SEC-only batch' in batch
    assert '000009223026000129/tfc-20260930.htm' in batch
    assert '000119312526423384/d186531d8k.htm' in batch
    for certification in ('TFCPRI120619.pdf', 'TFCPRO052820.pdf', 'TFCPRR080420.pdf'):
        assert certification in batch
    assert 'NYSEshvol20261112.pdf#page=170' in batch


def test_citizens_review_preserves_listed_classes_and_separate_g_redemption():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Citizens Financial Group · Three NYSE depositary share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, terms in zip('EHI', ('5.000% fixed', '7.375% fixed', '6.500% fixed-rate reset'), strict=True):
        assert f'`CFG-P{series}` / `CFG Pr{series}` / `CFG${series}` · Series {series} · {terms}\n' in batch
    assert '1/40 of its underlying preferred share' in batch
    assert 'October 6, 2030' in batch
    assert 'Series G was fully redeemed on October 6, 2026' in batch
    assert 'Series J issuance falls outside this batch' in batch
    assert '000075994426000213/cfg-20260930.htm' in batch
    assert '000119312526441754/d184921d8k.htm' in batch
    assert '000075994426000192/cfg-20261006.htm' in batch
    for certification in ('CFG102519.pdf', 'CFGPRH052324.pdf', 'CFGPRI073025.pdf'):
        assert certification in batch
    for page in (33, 34):
        assert f'NYSEshvol20261112.pdf#page={page}' in batch


def test_first_horizon_review_keeps_current_depositary_shares_and_redeemed_series_distinct():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**First Horizon · Three NYSE depositary share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('EFH', ('6.500%', '4.700%', '6.750%'), strict=True):
        assert f'`FHN-P{series}` / `FHN PR {series}` / `FHN${series}` · Series {series} · {rate}\n' in batch
    assert '1/4,000 of its underlying preferred share' in batch
    assert 'Series C was fully redeemed on May 1, 2026' in batch
    assert 'Series H was issued on March 12, 2026' in batch
    assert '000003696626000199/fhn-20260930.htm' in batch
    assert '000003696626000184/fhn-20261026.htm' in batch
    for certification in ('FHN8A061120.pdf', 'FHNPRF051021.pdf', 'FHNPRH031626.pdf'):
        assert certification in batch
    assert 'NYSEshvol20261112.pdf#page=64' in batch


def test_goldman_review_distinguishes_depositary_shares_from_trust_securities_and_notes():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Goldman Sachs · Three NYSE depositary share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series in 'ACD':
        assert f'`GS-P{series}` / `GS Pr{series}` / `GS${series}` · Series {series}\n' in batch
    assert '1/1,000 of a floating-rate non-cumulative preferred share' in batch
    assert 'directory-type gap for `GS$D`' in batch
    assert 'Series O and V were fully redeemed on November 10' in batch
    assert 'trust capital securities and medium-term notes fall outside this batch' in batch
    assert '000088698226000532/gs-20260930.htm' in batch
    assert '000119312526460732/d187542d8k.htm' in batch
    assert 'NYSEshvol20261112.pdf#page=78' in batch


def test_sce_review_distinguishes_trust_issuers_from_utility_guarantor():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Southern California Edison · Four NYSE trust preference securities matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, trust, rate in zip('GLMN', ('II', 'VI', 'VII', 'VIII'), ('5.10%', '5.00%', '7.50%', '6.95%'), strict=True):
        assert f'`SCE-P{series}` / `SCE PR {series}` / `SCE${series}` · Series {series} · SCE Trust {trust} · {rate}\n' in batch
    assert 'SCE is the guarantor and issues the underlying preference stock' in batch
    assert 'reports no Section 12(b) securities for SCE' in batch
    assert 'directory-type gaps for `SCE$L`, `SCE$M` and `SCE$N`' in batch
    assert 'Trust V Series K was redeemed in March 2026' in batch
    for source in ('d475965d8a12b.htm', 'scetrustviform8-a.htm', 'tmb-20231122x8a12b.htm',
                   'tmb-20240514x8a12b.htm', 'eix-20260930.htm', '000087666126000238/primary_doc.xml',
                   'NYSEshvol20261112.pdf#page=153'):
        assert source in batch


def test_pennymac_review_preserves_both_filed_symbols_and_dividend_dispute():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**PennyMac Mortgage Investment Trust · Three NYSE preferred share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('ABC', ('8.125%', '8.00%', '6.75%'), strict=True):
        assert f'`PMT-P{series}` / `PMT/PR{series}` / `PMT/P{series}` / `PMT${series}` · Series {series} · {rate}\n' in batch
    assert 'cumulative redeemable preferred shares of beneficial interest' in batch
    assert 'PennyMac reports that Series A and B retained their prior dividend rates' in batch
    assert 'The dispute remains pending as reported in the 10-Q' in batch
    assert 'no preferred shares were redeemed through September 30, 2026' in batch
    assert 'PMTU`, `PMTV` and `PMTW` are senior notes' in batch
    assert '000119312526445330/pmt-20260930.htm' in batch
    assert '000119312526437878/d179622d8k.htm' in batch
    assert 'NYSEshvol20261112.pdf#page=137' in batch


def test_epr_review_distinguishes_convertible_preferred_shares_from_redeemable_series_and_debt():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**EPR Properties · Three NYSE preferred share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    terms = ('5.75% cumulative convertible', '9.00% cumulative convertible', '5.75% cumulative redeemable')
    for series, term in zip('CEG', terms, strict=True):
        assert f'`EPR-P{series}` / `EPR Pr{series}` / `EPR${series}` · Series {series} · {term}\n' in batch
    assert 'directory-type gap for `EPR$E`' in batch
    assert 'September 30, 2026' in batch and '0.4433' in batch and '0.4866' in batch
    assert 'convertible senior notes fall outside this batch' in batch
    for source in ('000104545026000051/epr-20260930.htm', '000119312526456657/d488669d8k.htm',
                   '000104545026000050/ex993-eprx9302026supplemen.htm', 'NYSEshvol20261112.pdf#page=57'):
        assert source in batch


def test_stifel_review_distinguishes_listed_depositary_shares_from_notes_and_redeemed_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**Stifel Financial · Three NYSE depositary share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('BCD', ('6.25%', '6.125%', '4.50%'), strict=True):
        assert f'`SF-P{series}` / `SF Pr{series}` / `SF${series}` · Series {series} · {rate}\n' in batch
    assert '1/1,000 of a non-cumulative perpetual preferred share' in batch
    assert 'Series A was redeemed on August 20, 2021' in batch
    assert '`SFB` is the 5.20% senior notes listing' in batch
    assert 'from August 15, 2026, subject to regulatory approval' in batch
    assert 'Item 1 of the Series D Form 8-A says Series C once' in batch
    for source in ('000119312526446268/sf-20260930.htm', '000119312526427189/d182962d8k.htm',
                   'd46382d8a12b.htm', 'd46382dex998.htm', '000087666121001211/primary_doc.xml',
                   'SF-4Q26-Dividend-Announcement.pdf', 'NYSEshvol20261112.pdf#page=155'):
        assert source in batch


def test_tpg_mortgage_review_distinguishes_fixed_and_floating_preferred_shares_from_notes():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    start = '**TPG Mortgage Investment Trust · Three NYSE preferred share listings matched.**'
    assert start in review
    batch = review.split(start, 1)[1].split('\n- **', 1)[0]
    terms = ('8.25% fixed', '8.00% fixed', '8.000% original fixed rate, now floating')
    for series, term in zip('ABC', terms, strict=True):
        assert f'`MITT-P{series}` / `MITT Pr{series}` / `MITT${series}` · Series {series} · {term}\n' in batch
    assert 'cumulative redeemable preferred stock' in batch
    assert 'December 16, 2025' in batch and 'AG Mortgage Investment Trust' in batch
    assert 'September 17, 2024' in batch and 'CME Term SOFR' in batch
    assert '`MITN` and `MITP` are separate senior notes' in batch
    for source in ('000162828026071791/mitt-20260930.htm', '000162828026069770/mitt-20261104.htm',
                   '000162828025057427/a8k-121625xexhibit31.htm', 'NYSEshvol20261112.pdf#page=112'):
        assert source in batch


def test_costamare_review_maps_three_listed_series_and_excludes_other_preferred_shares():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**Costamare · Three NYSE preferred share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('BCD', ('7.625%', '8.50%', '8.75%'), strict=True):
        assert f'`CMRE-P{series}` / `CMRE.PR{series}` / `CMRE PR {series}` / `CMRE${series}` · Series {series} · {rate}\n' in batch
    assert 'cumulative redeemable perpetual preferred stock' in batch
    assert 'Series E was fully redeemed on July 15, 2024' in batch
    assert 'Series F sits outside the listed preferred classes' in batch
    assert 'Costamare Bulkers (`CMDB`) is a separate issuer' in batch
    for source in ('000114036126007868/ef20064083_20f.htm', '000117184326006324/exh_991.htm',
                   '000117184326006884/exh_991.htm', 'NYSEshvol20261112.pdf#page=38'):
        assert source in batch


def test_compass_review_distinguishes_the_trust_preferred_share_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**Compass Diversified Holdings · Three NYSE preferred share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    terms = ('7.250% fixed, noncumulative', '7.875% fixed-to-floating, cumulative', '7.875% fixed, cumulative')
    for series, term in zip('ABC', terms, strict=True):
        assert f'`CODI-P{series}` / `CODI PR {series}` / `CODI${series}` · Series {series} · {term}\n' in batch
    assert 'beneficial interests in the trust' in batch
    assert 'LLC is a separate co-registrant' in batch
    assert 'April 30, 2028' in batch
    assert 'declared for payment on October 30, 2026' in batch
    assert 'common shares are outside this batch' in batch
    for source in ('000134512626000071/codi-20260930.htm', '000134512626000072/codi-20261104.htm',
                   '000134512626000065/codidistributionpressrelea.htm', 'NYSEshvol20261112.pdf#page=39'):
        assert source in batch


def test_pinnacle_review_uses_post_merger_classes_and_documents_directory_conflicts():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**Pinnacle Financial Partners · Three NYSE preferred security listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    terms = ('fixed-to-floating preferred stock', 'fixed-rate reset preferred stock',
             'depositary shares, each representing 1/40 of a 6.75% fixed-rate preferred share')
    for series, term in zip('ABC', terms, strict=True):
        assert f'`PNFP-P{series}` / `PNFP - Pr{series}` / `PNFP${series}` · Series {series} · {term}\n' in batch
    assert 'noncumulative perpetual preferred stock' in batch
    assert 'directory describes both B and C as fixed-to-floating stock' in batch
    assert 'Series D and E became Series A and B' in batch
    assert '`PNFPP` depositary shares converted into the new Series C depositary shares' in batch
    for source in ('000208286626000092/pnfp-20260930.htm', '000208286626000094/pnfp-20261104.htm',
                   '000114036126000050/ef20061822_8k12b.htm', '000087666125001026/PNFP123125.pdf',
                   'NYSEshvol20261112.pdf#page=137'):
        assert source in batch


def test_gabelli_equity_trust_review_matches_listed_series_and_resolves_the_h_type_gap():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**Gabelli Equity Trust · Three NYSE preferred share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    for series in 'GHK':
        assert f'`GAB-P{series}` / `GAB Pr {series}` / `GAB${series}` · Series {series}\n' in batch
    assert '5.00% fixed cumulative preferred stock' in batch
    assert 'directory-type gap for `GAB$H`' in batch
    assert 'Series M and Q are off-exchange' in batch
    assert 'auction-rate Series C and E were redeemed in 2024' in batch
    for source in ('000182912626004782/gab_8k.htm', '000182912626009842/gab_ncsrs.htm',
                   '000182912626003035/gabelliequitytrust_424b4.htm', 'NYSEshvol20261112.pdf#page=71'):
        assert source in batch


def test_renaissancere_review_maps_the_two_depositary_classes_and_separates_redeemed_series():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**RenaissanceRe · Two NYSE depositary share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('FG', ('5.750%', '4.20%'), strict=True):
        assert f'`RNR-P{series}` / `RNR PR{series}` / `RNR${series}` · Series {series} · {rate}\n' in batch
    assert '1/1,000 of the corresponding noncumulative preference share' in batch
    assert 'Series E was redeemed on August 11, 2021' in batch
    for source in ('000091314426000098/rnr-20260930.htm', '000091314426000096/rnr-20261027.htm',
                   '000091314421000110/rnr-20210930.htm', 'NYSEshvol20261112.pdf#page=148'):
        assert source in batch


def test_bank_of_hawaii_review_maps_both_depositary_classes_and_distinguishes_the_call_option():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**Bank of Hawaii · Two NYSE depositary share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('AB', ('4.375%', '8.000%'), strict=True):
        assert f'`BOH-P{series}` / `BOH.PR{series}` / `BOH${series}` · Series {series} · {rate}\n' in batch
    assert '1/40 of the corresponding fixed-rate noncumulative perpetual preferred share' in batch
    assert 'Series A became eligible for optional redemption' in batch and 'August 1, 2026' in batch
    assert 'declared for payment on November 2, 2026' in batch
    for source in ('000004619526000065/boh-20260930.htm', '000004619526000062/boh-20261026.htm',
                   '000087666121000894/BOH061521.pdf', '000087666124000513/BOHPRB062424.pdf',
                   'NYSEshvol20261112.pdf#page=26'):
        assert source in batch


def test_synchrony_review_maps_listed_depositary_classes_and_preserves_the_reset_terms():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**Synchrony Financial · Two NYSE depositary share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    for series, terms in zip('AB', ('5.625% fixed', '8.250% initial fixed rate'), strict=True):
        assert f'`SYF-P{series}` / `SYFPr{series}` / `SYF${series}` · Series {series} · {terms}\n' in batch
    assert '1/40 of the corresponding noncumulative perpetual preferred share' in batch
    assert 'May 15, 2029 and every five years after that' in batch
    assert 'five-year Treasury rate plus 4.044 percentage points' in batch
    assert 'Series C is a separate 1/100 depositary issuance' in batch
    for source in ('000160171226000043/syf-20260930.htm', '000160171226000045/syf-20261110.htm',
                   '000087666124000111/SYFPRB022324.pdf', 'NYSEshvol20261112.pdf#page=167'):
        assert source in batch


def test_american_homes_review_distinguishes_listed_preferred_shares_from_partnership_units():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**American Homes 4 Rent · Two NYSE preferred share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('GH', ('5.875%', '6.250%'), strict=True):
        assert f'`AMH-P{series}` / `AMH-{series}` / `AMH${series}` · Series {series} · {rate}\n' in batch
    assert 'cumulative redeemable perpetual preferred shares' in batch
    assert 'operating partnership units are separate' in batch
    assert 'Series F was redeemed on May 5, 2022' in batch
    for source in ('000156240126000058/amh-20260930.htm', '000156240126000061/amh-20261112.htm',
                   'NYSEshvol20261112.pdf#page=9'):
        assert source in batch


def test_rexford_review_maps_both_listed_classes_and_preserves_the_redemption_boundary():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    heading = '**Rexford Industrial Realty · Two NYSE preferred share listings matched.**'
    assert heading in review
    batch = review.split(heading, 1)[1].split('\n- **', 1)[0]
    for series, rate in zip('BC', ('5.875%', '5.625%'), strict=True):
        assert f'`REXR-P{series}` / `REXR PR{series}` / `REXR${series}` · Series {series} · {rate}\n' in batch
    assert 'cumulative redeemable preferred stock' in batch
    assert 'operating partnership units are separate' in batch
    assert 'Series A was redeemed on August 16, 2021' in batch
    for source in ('000157128326000064/rexr-20260930.htm', '000157128326000058/rexr-20261022.htm',
                   '000157128321000045/rexr-20210930.htm', 'NYSEshvol20261112.pdf#page=146'):
        assert source in batch


def test_dated_listing_gap_review_is_limited_to_personal_research(monkeypatch):
    from src.listing_gap_review import listing_gap_review_markdown

    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    assert listing_gap_review_markdown() == ''
