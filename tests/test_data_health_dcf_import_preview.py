import pandas as pd

from src.data_health_dcf_import_preview import dcf_import_preview_cards, dcf_import_preview_frame


def test_dcf_import_preview_blocks_placeholder_source_fields():
    source_frame = pd.DataFrame(
        [
            {
                "Ticker": "META",
                "Input Family": "shares_outstanding",
                "Missing DCF Fields": "shares_outstanding",
                "Source Type": "<source_type>",
                "Source File Or URL": "<source_file_or_url>",
                "Source As Of Date": "<source_as_of_date>",
                "Reviewer": "<reviewer>",
                "Review Date": "<review_date>",
                "Source Proof Status": "not_reviewed",
                "Validation Result": "not_run",
                "Preview Result": "not_run",
                "Apply Decision": "not_reviewed",
            }
        ]
    )

    preview = dcf_import_preview_frame(source_frame, "shares_outstanding")
    cards = dcf_import_preview_cards(preview)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()
    table_text = " ".join(str(value) for value in preview.to_numpy().flatten()).lower()

    assert preview.iloc[0]["Status"] == "blocked"
    assert preview.iloc[2]["Status"] == "blocked"
    assert "source_file_or_url" in preview.iloc[0]["Review Boundary"]
    assert "blocked until reviewed fields are complete" in table_text
    assert "fundamentals row preview: blocked" in rendered
    assert "header, row, validate, preview, apply boundary" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered


def test_dcf_import_preview_keeps_validate_preview_apply_boundary_when_ready():
    source_frame = pd.DataFrame(
        [
            {
                "Ticker": "META",
                "Input Family": "shares_outstanding",
                "Missing DCF Fields": "shares_outstanding",
                "Period": "FY2025",
                "Shares Outstanding": "123456789",
                "Source Type": "10-K",
                "Source File Or URL": "https://www.sec.gov/example",
                "Source As Of Date": "2026-03-31",
                "Reviewer": "reviewer",
                "Review Date": "2026-06-19",
                "Source Proof Status": "reviewed",
                "Validation Result": "pass",
                "Preview Result": "reviewed",
                "Apply Decision": "skipped_after_review",
            }
        ]
    )

    preview = dcf_import_preview_frame(source_frame, "shares_outstanding")
    table_text = " ".join(str(value) for value in preview.to_numpy().flatten()).lower()

    assert preview.iloc[0]["Status"] == "ready_for_validate_preview"
    assert preview.iloc[2]["Status"] == "ready"
    assert "make imports-validate" in table_text
    assert "make imports-preview" in table_text
    assert "run make imports-apply only after imports-preview" in table_text
    assert "rebuild readiness and report before any supported proof outcome" in table_text
