import os

from src.provider_env import load_provider_environment, reset_provider_environment_cache
from src.data_update import make_price_source, PriceSourceLadder


def test_load_provider_environment_reads_local_files_without_overriding_exported_env(tmp_path, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "already-exported")
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)
    reset_provider_environment_cache()

    (tmp_path / ".env").write_text(
        "# local provider keys\n"
        "FMP_API_KEY=file-value\n"
        "ALPHA_VANTAGE_API_KEY=alpha-from-env\n",
        encoding="utf-8",
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "provider_keys.env").write_text(
        "ALPHA_VANTAGE_API_KEY=alpha-from-config\n"
        "FINNHUB_API_KEY='finnhub-from-config'\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "ALPHA_VANTAGE_API_KEY=alpha-from-local\n"
        "STOOQ_API_KEY=stooq-from-local\n",
        encoding="utf-8",
    )

    summary = load_provider_environment(tmp_path, force=True)

    assert os.environ["FMP_API_KEY"] == "already-exported"
    assert os.environ["ALPHA_VANTAGE_API_KEY"] == "alpha-from-local"
    assert os.environ["FINNHUB_API_KEY"] == "finnhub-from-config"
    assert os.environ["STOOQ_API_KEY"] == "stooq-from-local"
    assert summary["loaded_keys"] == [
        "ALPHA_VANTAGE_API_KEY",
        "FINNHUB_API_KEY",
        "STOOQ_API_KEY",
    ]
    assert "already-exported" not in str(summary)
    assert "alpha-from-local" not in str(summary)


def test_auto_price_source_uses_local_provider_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    reset_provider_environment_cache()

    (tmp_path / ".env").write_text(
        "FMP_API_KEY=fmp-from-file\n"
        "FINNHUB_API_KEY=finnhub-from-file\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    source = make_price_source("auto")

    assert isinstance(source, PriceSourceLadder)
    assert source.provider_names == ["yahoo", "stooq", "fmp", "finnhub"]
