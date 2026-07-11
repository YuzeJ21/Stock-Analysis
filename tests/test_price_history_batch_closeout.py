from pathlib import Path

from src.price_history_proof_queue import PriceHistoryProofRow


def _row(ticker: str, *, reviewed: bool) -> PriceHistoryProofRow:
    return PriceHistoryProofRow(
        priority=1,
        ticker=ticker,
        state="partial",
        current_history_rows=20,
        next_goal="Unlock Monthly Picks",
        target_history_rows=40,
        rows_needed=20,
        first_local_date="2026-01-01",
        latest_local_date="2026-01-20",
        next_safe_command="wait for new verified OHLCV source or changed provider behavior",
        dry_run_batch_command="make price-refresh-loop DRY_RUN=1",
        validate_preview_apply_gate="make price-validate -> make price-preview",
        post_run_proof_command="make readiness",
        stop_rule="Keep the state visible.",
        source_note=(
            "Reviewed proof ledger already records this short-history source path as non-actionable."
            if reviewed
            else "Uses local price worklist thresholds."
        ),
    )


def test_batch_closeout_groups_reviewed_source_limited_tickers_in_copy_only_scaffold():
    from src.price_history_batch_closeout import render_price_history_batch_closeout

    rendered = render_price_history_batch_closeout(
        [_row("NVDA", reviewed=True), _row("AMD", reviewed=True)], top_n=25
    )
    lowered = rendered.lower()

    assert "read-only" in lowered
    assert "does not refresh, write data, record proof rows, stage, commit, push, or expose secrets" in lowered
    assert "reviewed source-limited price-history outcomes only" in lowered
    assert "Grouped tickers: AMD, NVDA" in rendered
    assert "DRY_RUN=1 make reviewed-batch-proof-record" in rendered
    assert "LANE=price_history" in rendered
    assert "FINAL_OUTCOME=still_blocked" in rendered
    assert "TICKERS=AMD,NVDA" in rendered


def test_batch_closeout_reports_when_no_reviewed_source_limited_rows_exist():
    from src.price_history_batch_closeout import render_price_history_batch_closeout

    rendered = render_price_history_batch_closeout([_row("AMD", reviewed=False)], top_n=25)

    assert "No reviewed source-limited price-history outcomes found for the selected scope." in rendered
    assert "reviewed-batch-proof-record" not in rendered


def test_batch_closeout_cli_accepts_path_scope_and_top_n_arguments(tmp_path: Path, monkeypatch, capsys):
    import src.price_history_batch_closeout as closeout

    captured: dict[str, object] = {}

    def fake_queue_builder(root, *, data_dir, output_dir, top_n, tickers, include_reviewed):
        captured.update(
            root=root,
            data_dir=data_dir,
            output_dir=output_dir,
            top_n=top_n,
            tickers=tickers,
            include_reviewed=include_reviewed,
        )
        return [_row("NVDA", reviewed=True), _row("AMD", reviewed=True)]

    monkeypatch.setattr(closeout, "build_price_history_proof_queue_from_files", fake_queue_builder)

    assert closeout.main(
        [
            "--project-root",
            str(tmp_path),
            "--data-dir",
            "fixture-data",
            "--outputs-dir",
            "fixture-outputs",
            "--top-n",
            "1",
            "--tickers",
            "nvda,amd",
        ]
    ) == 0

    assert captured["root"] == tmp_path.resolve()
    assert captured["data_dir"] == (tmp_path / "fixture-data").resolve()
    assert captured["output_dir"] == (tmp_path / "fixture-outputs").resolve()
    assert captured["top_n"] is None
    assert captured["tickers"] == ["NVDA", "AMD"]
    assert captured["include_reviewed"] is True
    assert "Grouped tickers: AMD" in capsys.readouterr().out


def test_batch_closeout_cli_limits_reviewed_rows_after_mixed_queue_selection(tmp_path: Path, monkeypatch, capsys):
    import src.price_history_batch_closeout as closeout

    captured: dict[str, object] = {}
    queue_rows = [
        _row("UNR1", reviewed=False),
        _row("UNR2", reviewed=False),
        _row("AMD", reviewed=True),
        _row("NVDA", reviewed=True),
        _row("ZZZ", reviewed=True),
    ]

    def fake_queue_builder(root, *, data_dir, output_dir, top_n, tickers, include_reviewed):
        captured["top_n"] = top_n
        return queue_rows if top_n is None else queue_rows[:top_n]

    monkeypatch.setattr(closeout, "build_price_history_proof_queue_from_files", fake_queue_builder)

    assert closeout.main(["--project-root", str(tmp_path), "--top-n", "2"]) == 0

    assert captured["top_n"] is None
    assert "Grouped tickers: AMD, NVDA" in capsys.readouterr().out


def test_batch_closeout_does_not_import_mutating_ledger_functions():
    source = Path("src/price_history_batch_closeout.py").read_text(encoding="utf-8")

    assert "src.reviewed_batch_proof" not in source
    assert "append_reviewed_batch_proof" not in source
    assert "write_reviewed_batch_proofs" not in source
