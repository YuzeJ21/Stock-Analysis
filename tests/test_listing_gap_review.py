def test_dated_listing_gap_review_preserves_both_populations_and_the_original_inventory():
    from src.listing_gap_review import listing_gap_review_markdown

    review = listing_gap_review_markdown()
    assert '2026-11-12' in review and '13,791' in review and '38 test issues excluded' in review
    assert '544 SEC-only' in review and '282 unresolved directory types' in review
    assert '246' in review and '19' in review and '17' in review
    assert '96 were reviewed, with 448 still unreviewed' in review and '274 still unreviewed' in review
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


def test_dated_listing_gap_review_is_limited_to_personal_research(monkeypatch):
    from src.listing_gap_review import listing_gap_review_markdown

    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1')
    assert listing_gap_review_markdown() == ''
