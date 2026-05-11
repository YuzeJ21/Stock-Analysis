from pathlib import Path

from src.providers.local_schemas import validate_local_dataset


def test_validate_sparse_fundamentals_csv_is_valid_with_warnings(tmp_path: Path):
    path = tmp_path / "fundamentals.csv"
    path.write_text(
        "ticker,pe_ratio,revenue_growth,profit_margin,debt_to_equity\n"
        "NVDA,34,0.28,0.34,0.4\n",
        encoding="utf-8",
    )

    result, frame = validate_local_dataset("fundamentals", path)

    assert result.status == "valid_with_warnings"
    assert frame is not None
    assert result.missing_required_columns == []


def test_validate_rich_fundamentals_csv_is_valid(tmp_path: Path):
    path = tmp_path / "fundamentals.csv"
    path.write_text(
        "ticker,revenue,eps,free_cash_flow,fcf_margin,shares_outstanding,as_of_date\n"
        "ALFA,1000,6,120,0.12,10,2026-05-01\n",
        encoding="utf-8",
    )

    result, _ = validate_local_dataset("fundamentals", path)

    assert result.status == "valid"
    assert "revenue" in result.available_optional_columns


def test_validate_missing_required_ticker_column_is_invalid(tmp_path: Path):
    path = tmp_path / "fundamentals.csv"
    path.write_text("revenue,eps\n1000,5\n", encoding="utf-8")

    result, _ = validate_local_dataset("fundamentals", path)

    assert result.status == "invalid"
    assert result.missing_required_columns == ["ticker"]


def test_validate_unknown_extra_columns_warns_but_does_not_fail(tmp_path: Path):
    path = tmp_path / "fundamentals.csv"
    path.write_text(
        "ticker,pe_ratio,mystery_field\n"
        "NVDA,34,hello\n",
        encoding="utf-8",
    )

    result, _ = validate_local_dataset("fundamentals", path)

    assert result.status == "valid_with_warnings"
    assert result.unknown_columns == ["mystery_field"]


def test_validate_invalid_numeric_values_warns(tmp_path: Path):
    path = tmp_path / "fundamentals.csv"
    path.write_text(
        "ticker,pe_ratio\n"
        "NVDA,not_a_number\n",
        encoding="utf-8",
    )

    result, frame = validate_local_dataset("fundamentals", path)

    assert result.status == "valid_with_warnings"
    assert any("numeric" in warning for warning in result.warnings)
    assert frame is not None
    assert frame["pe_ratio"].isna().all()


def test_validate_invalid_date_values_warns(tmp_path: Path):
    path = tmp_path / "earnings.csv"
    path.write_text(
        "ticker,next_earnings_date\n"
        "NVDA,not_a_date\n",
        encoding="utf-8",
    )

    result, frame = validate_local_dataset("earnings", path)

    assert result.status == "valid_with_warnings"
    assert any("parsed as dates" in warning for warning in result.warnings)
    assert frame is not None
    assert frame["next_earnings_date"].isna().all()


def test_validate_missing_optional_file_reports_missing_file(tmp_path: Path):
    result, frame = validate_local_dataset("analyst_estimates", tmp_path / "analyst_estimates.csv")

    assert result.status == "missing_file"
    assert frame is None
