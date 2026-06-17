from __future__ import annotations

from pathlib import Path

from scripts.diff_hygiene import StatusEntry
from src import data_health_generated_churn as generated_churn


def test_generated_churn_review_classifies_generated_artifacts(monkeypatch):
    entries = [
        StatusEntry("M", "src/dashboard.py"),
        StatusEntry("M", "data/reports/ticker_readiness_report.csv"),
        StatusEntry("??", "outputs/research_action_queue.csv"),
        StatusEntry("M", "outputs/stock_reports/nvda.md"),
        StatusEntry("M", "scratch/local.txt"),
    ]
    monkeypatch.setattr(generated_churn, "diff_hygiene_load_status", lambda _root: entries)

    frame = generated_churn.generated_churn_review_frame(Path("."))
    detail = generated_churn.generated_churn_detail_frame(Path("."))
    cards = generated_churn.generated_churn_review_cards(Path("."))
    rendered = " ".join(
        frame.astype(str).to_numpy().flatten().tolist()
        + detail.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    generated = frame.loc[frame["Bucket"].eq("Generated CSV/JSON churn")].iloc[0]
    product = frame.loc[frame["Bucket"].eq("Product/code/docs/tests")].iloc[0]
    reports = frame.loc[frame["Bucket"].eq("Markdown sample reports")].iloc[0]
    manual = frame.loc[frame["Bucket"].eq("Manual-review paths")].iloc[0]

    assert int(generated["Files"]) == 2
    assert int(generated["Changed"]) == 1
    assert int(generated["New"]) == 1
    assert int(product["Files"]) == 1
    assert int(reports["Files"]) == 1
    assert int(manual["Files"]) == 1
    assert detail["Path"].tolist() == ["data/reports/ticker_readiness_report.csv", "outputs/research_action_queue.csv"]
    assert cards[0]["title"] == "2 generated artifact(s) excluded by default"
    assert cards[0]["command"] == "make diff-hygiene-files"
    assert "generated csv/json churn should stay local" in rendered
    assert "reviewed evidence" in rendered
    assert "safe staging" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_generated_churn_review_cards_product_only_boundary(monkeypatch):
    entries = [StatusEntry("M", "src/dashboard.py")]
    monkeypatch.setattr(generated_churn, "diff_hygiene_load_status", lambda _root: entries)

    cards = generated_churn.generated_churn_review_cards(Path("."))
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "No generated churn detected"
    assert cards[0]["command"] == "make staged-hygiene-check"
    assert "product files: 1" in rendered
    assert "stage product files only after review" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
