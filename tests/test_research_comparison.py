from types import SimpleNamespace

import pandas as pd
import pytest

from src.research_comparison import build_research_comparison, comparison_matrix_rows


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": "NVDA",
                "Asset Type": "company",
                "Research State": "Research Now",
                "Readiness": "ready",
                "Price Ready": True,
                "Fundamentals Ready": True,
                "DCF Ready": True,
                "Trusted Peer Ready": True,
                "Supported Now": "Price, DCF, and trusted peer context.",
                "Blocked / Missing": "Optional earnings context.",
                "Next Proof Step": "Review optional source evidence.",
                "Proof Freshness": "Current snapshot.",
            },
            {
                "Ticker": "AMD",
                "Asset Type": "company",
                "Research State": "Monitor",
                "Readiness": "partial",
                "Price Ready": True,
                "Fundamentals Ready": True,
                "DCF Ready": True,
                "Trusted Peer Ready": False,
                "Supported Now": "Price and DCF context; candidate peers only.",
                "Blocked / Missing": "Trusted peer evidence.",
                "Next Proof Step": "Review source-backed peer relationships.",
                "Proof Freshness": "Current snapshot.",
            },
        ]
    )


def test_comparison_requires_two_or_three_unique_tickers():
    with pytest.raises(ValueError, match="two or three"):
        build_research_comparison(_rows().head(1), journal_states={})
    with pytest.raises(ValueError, match="two or three"):
        build_research_comparison(pd.concat([_rows(), _rows().head(1), _rows().tail(1)]), journal_states={})
    with pytest.raises(ValueError, match="unique"):
        build_research_comparison(pd.concat([_rows().head(1), _rows().head(1)]), journal_states={})


def test_comparison_preserves_selection_order_and_readiness_boundaries():
    comparison = build_research_comparison(_rows().iloc[[1, 0]], journal_states={})

    assert [company.ticker for company in comparison.companies] == ["AMD", "NVDA"]
    assert comparison.companies[0].dcf_state == "Ready"
    assert comparison.companies[0].trusted_peer_state == "Blocked"
    assert comparison.companies[1].trusted_peer_state == "Ready"


def test_candidate_peer_copy_does_not_promote_trusted_peer_readiness():
    comparison = build_research_comparison(_rows().iloc[[1, 0]], journal_states={})

    amd = comparison.companies[0]
    assert "candidate peers" in amd.supported_now
    assert amd.trusted_peer_state == "Blocked"


def test_comparison_uses_only_supplied_reviewed_journal_catalysts_and_risks():
    journal_states = {
        "NVDA": SimpleNamespace(
            catalysts=(SimpleNamespace(summary="Reviewed product-cycle evidence."),),
            risks=(SimpleNamespace(summary="Reviewed supply constraint evidence."),),
        )
    }

    comparison = build_research_comparison(_rows(), journal_states=journal_states)

    assert comparison.companies[0].catalysts == "Reviewed product-cycle evidence."
    assert comparison.companies[0].risks == "Reviewed supply constraint evidence."
    assert comparison.companies[1].catalysts == "No reviewed catalyst evidence."
    assert comparison.companies[1].risks == "No reviewed risk evidence."


def test_comparison_matrix_has_no_rank_score_or_transaction_language():
    rows = _rows()
    rows.loc[0, "Next Proof Step"] = "Buy after review"
    comparison = build_research_comparison(rows, journal_states={})

    matrix = comparison_matrix_rows(comparison)
    rendered = " ".join(str(value) for row in matrix for value in row.values()).lower()

    assert "score" not in rendered
    assert "winner" not in rendered
    assert "rank" not in rendered
    for prohibited in ("buy", "sell", "hold", "order", "recommendation", "expected return"):
        assert prohibited not in rendered
