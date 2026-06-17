from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.diff_hygiene import StatusEntry
from scripts.diff_hygiene import group_entries as diff_hygiene_group_entries, load_status as diff_hygiene_load_status


def generated_churn_review_frame(repo_root: Path | str) -> pd.DataFrame:
    columns = [
        "Bucket",
        "Files",
        "Changed",
        "New",
        "Default Decision",
        "Review Boundary",
        "Safe Command",
    ]
    entries = diff_hygiene_load_status(Path(repo_root))
    groups = diff_hygiene_group_entries(entries)

    def _row(bucket: str, key: str, decision: str, boundary: str, command: str) -> dict[str, object]:
        items = groups[key]
        new_count = sum(1 for item in items if item.status in {"??", "A"})
        return {
            "Bucket": bucket,
            "Files": len(items),
            "Changed": len(items) - new_count,
            "New": new_count,
            "Default Decision": decision,
            "Review Boundary": boundary,
            "Safe Command": command,
        }

    return pd.DataFrame(
        [
            _row(
                "Product/code/docs/tests",
                "product_candidate",
                "stage when intentional",
                "Stage only after product review and public wording checks.",
                "git add -- <product files> && make staged-hygiene-check",
            ),
            _row(
                "Markdown sample reports",
                "sample_report_candidate",
                "review individually",
                "Stage only if the regenerated report is intentional public/demo evidence.",
                "make diff-hygiene-files",
            ),
            _row(
                "Generated CSV/JSON churn",
                "generated_csv_churn",
                "exclude by default",
                "Do not stage unless the exact artifact is intentionally reviewed evidence.",
                "make diff-hygiene-files && inspect outputs/staging/generated_churn.txt",
            ),
            _row(
                "Manual-review paths",
                "review_manually",
                "stop and inspect",
                "Inspect before staging; classifier does not know whether these are public-safe.",
                "make diff-hygiene",
            ),
        ],
        columns=columns,
    )


def generated_churn_detail_frame(repo_root: Path | str, *, limit: int = 80) -> pd.DataFrame:
    columns = ["Status", "Path", "Default Decision", "Review Boundary"]
    entries = diff_hygiene_load_status(Path(repo_root))
    groups = diff_hygiene_group_entries(entries)
    rows: list[dict[str, object]] = []
    for item in groups["generated_csv_churn"][: max(limit, 0)]:
        rows.append(
            {
                "Status": item.status or "M",
                "Path": item.path,
                "Default Decision": "exclude by default",
                "Review Boundary": "Keep local unless this exact generated artifact is selected as reviewed evidence.",
            }
        )
    return pd.DataFrame(rows, columns=columns)


def generated_churn_review_cards(repo_root: Path | str) -> list[dict[str, object]]:
    frame = generated_churn_review_frame(repo_root)
    if frame.empty:
        return [
            {
                "kicker": "GENERATED CHURN",
                "title": "No dirty files detected",
                "body": "Working tree is clean. Keep using diff hygiene before staging future product changes.",
                "badges": ["clean", "read-only"],
                "command": "make diff-hygiene-summary",
            }
        ]
    generated = frame.loc[frame["Bucket"].eq("Generated CSV/JSON churn")]
    product = frame.loc[frame["Bucket"].eq("Product/code/docs/tests")]
    manual = frame.loc[frame["Bucket"].eq("Manual-review paths")]
    generated_count = int(generated["Files"].iloc[0]) if not generated.empty else 0
    product_count = int(product["Files"].iloc[0]) if not product.empty else 0
    manual_count = int(manual["Files"].iloc[0]) if not manual.empty else 0
    if generated_count:
        title = f"{generated_count} generated artifact(s) excluded by default"
        body = (
            f"Product files: {product_count}. Manual-review paths: {manual_count}. "
            "Generated CSV/JSON churn should stay local unless the exact file is reviewed evidence."
        )
        badges = ["exclude generated churn", "safe staging"]
        command = "make diff-hygiene-files"
    else:
        title = "No generated churn detected"
        body = f"Product files: {product_count}. Manual-review paths: {manual_count}. Stage product files only after review."
        badges = ["product-only", "safe staging"]
        command = "make staged-hygiene-check"
    return [
        {
            "kicker": "GENERATED CHURN",
            "title": title,
            "body": body,
            "badges": badges,
            "command": command,
        }
    ]
