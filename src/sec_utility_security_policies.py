"""Exact SEC source contracts for two multi-symbol utility issuers."""

UTILITY_POLICIES = (
    {
        "policy_id": "so-selected-common-2026-v1",
        "ticker": "SO",
        "sec_cik": "0000092122",
        "issuer_symbols": ["SO", "SOJC", "SOJD", "SOJE", "SOJF", "SOMN"],
        "kind": "supported_common",
        "reason": "literal_common_scope_supported",
        "basis_fact_ids": ["f-606"],
        "documents": {
            "annual": {
                "metadata": {
                    "form": "10-K",
                    "reportDate": "2025-12-31",
                    "filingDate": "2026-02-19",
                    "acceptanceDateTime": "2026-02-18T22:46:14.000Z",
                    "accessionNumber": "0000092122-26-000006",
                    "primaryDocument": "so-20251231.htm",
                    "isInlineXBRL": 1,
                    "isXBRL": 1,
                },
                "cover_fact_ids": ["f-66", "f-67", "f-68"],
                "sha256": "e9617a201f3ef73a84735f6cc7bbbf6e7c0653a1ceaf7c032fba594583ec8d19",
                "normalization": "sec-empty-tail-script-v1",
                "body_sha256": "46aea07b6bd44b32b75014da650ae2610949a487927dd53b16f239110a734c7e",
            },
            # The charter amendment in accession 0000092122-26-000040
            # reduced par value for the existing common stock.
            "cover": {
                "metadata": {
                    "form": "8-K",
                    "reportDate": "2026-11-12",
                    "filingDate": "2026-11-17",
                    "acceptanceDateTime": "2026-11-17T19:16:00.000Z",
                    "accessionNumber": "0000092122-26-000082",
                    "primaryDocument": "so-20261112.htm",
                    "isInlineXBRL": 1,
                    "isXBRL": 1,
                },
                "cover_fact_ids": ["f-17", "f-18", "f-19"],
                "sha256": "e56dbf4f003a64afa9bb4ada3ae43db985eb6f82d87613220424feb7eafa7cbd",
                "normalization": "sec-empty-tail-script-v1",
                "body_sha256": "a8d6607d22b1599231341e0d279a7e25d056ea38849f55d5f4ee42e83a7c95e3",
            },
        },
    },
    {
        "policy_id": "nee-selected-common-2026-v1",
        "ticker": "NEE",
        "sec_cik": "0000753308",
        "issuer_symbols": ["NEE", "NEE-PN", "NEE-PS", "NEE-PT", "NEE-PU", "NEE-PV", "NEE-PW"],
        "kind": "supported_common",
        "reason": "literal_common_scope_supported",
        "basis_fact_ids": ["f-286", "f-2587", "f-2588"],
        "documents": {
            "annual": {
                "metadata": {
                    "form": "10-K",
                    "reportDate": "2025-12-31",
                    "filingDate": "2026-02-13",
                    "acceptanceDateTime": "2026-02-13T21:19:14.000Z",
                    "accessionNumber": "0000753308-26-000015",
                    "primaryDocument": "nee-20251231.htm",
                    "isInlineXBRL": 1,
                    "isXBRL": 1,
                },
                "cover_fact_ids": ["f-16", "f-17", "f-18"],
                "sha256": "705b82c6cd3f5348a4870370e415c65b263716abb4c9f20dba6dd48292affbe5",
                "normalization": "sec-empty-tail-script-v1",
                "body_sha256": "c9acc48394834880be0f585f88826d7ed2747cc59c31a293e0664aac78192249",
            },
            "cover": {
                "metadata": {
                    "form": "8-K",
                    "reportDate": "2026-11-05",
                    "filingDate": "2026-11-05",
                    "acceptanceDateTime": "2026-11-05T21:58:54.000Z",
                    "accessionNumber": "0000753308-26-000084",
                    "primaryDocument": "nee-20261105.htm",
                    "isInlineXBRL": 1,
                    "isXBRL": 1,
                },
                "cover_fact_ids": ["f-17", "f-18", "f-19"],
                "sha256": "46723791961232c740c7f1bbb8adbe9028656848d45120b97c70c1aa401ee999",
                "normalization": "sec-empty-tail-script-v1",
                "body_sha256": "7e7e787a7da66063893674f3433db840ed15f5f9ff3222485450161f256e17ee",
            },
        },
    },
)
