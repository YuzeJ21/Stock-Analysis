def test_dated_listing_gap_review_preserves_both_populations_and_the_original_inventory():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert '2026-11-12' in review and '13,791' in review and '38 test issues excluded' in review
    assert '544 SEC-only' in review and '282 unresolved directory types' in review
    assert '246' in review and '19' in review and '17' in review
    assert '137 were reviewed, with 407 still unreviewed' in review and '273 still unreviewed' in review
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


def test_dated_listing_gap_review_is_limited_to_personal_research(monkeypatch):
    from src.listing_gap_review import listing_gap_review_markdown

    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    assert listing_gap_review_markdown() == ''
