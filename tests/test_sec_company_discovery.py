"""Behavioral tests for session-only SEC company candidate search."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest


def _payload(rows: list[list[object]]) -> bytes:
    return json.dumps(
        {"fields": ["cik", "name", "ticker", "exchange"], "data": rows},
        separators=(",", ":"),
    ).encode("utf-8")


def test_online_search_returns_source_bound_exact_ticker_candidate() -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    raw = _payload([[1045810, "NVIDIA CORPORATION", "NVDA", "Nasdaq"]])
    result = search_sec_company_candidates(
        "nvda",
        user_agent="Research Tool contact@example.com",
        fetcher=lambda _url, _agent: (
            raw,
            {"Last-Modified": "Thu, 29 Oct 2026 14:00:00 GMT"},
        ),
        observed_at=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
    )

    assert result == {
        "status": "ready",
        "query": "nvda",
        "candidates": [
            {
                "ticker": "NVDA",
                "cik": "0001045810",
                "title": "NVIDIA CORPORATION",
                "exchange": "Nasdaq",
                "ambiguous": False,
            }
        ],
        "source_url": "https://www.sec.gov/files/company_tickers_exchange.json",
        "observed_at": "2026-10-30T12:00:00Z",
        "source_last_modified": "2026-10-29T14:00:00Z",
        "payload_sha256": hashlib.sha256(raw).hexdigest(),
    }


def test_name_search_preserves_ambiguous_ticker_ciks_and_deduplicates_pairs() -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    raw = _payload([
        [1001, "Alpine Devices", "ALP", "Nasdaq"],
        [1001, "Alpine Devices", "ALP", "Nasdaq"],
        [1002, "Alpine Holdings", "ALP", "NYSE"],
        [1003, "Alpine Mining", "AMIN", None],
    ])
    result = search_sec_company_candidates(
        "alpine",
        user_agent="Research Tool contact@example.com",
        fetcher=lambda _url, _agent: (raw, {}),
        observed_at=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
    )

    assert result["status"] == "ready"
    assert result["source_last_modified"] is None
    assert result["candidates"] == [
        {"ticker": "ALP", "cik": "0000001001", "title": "Alpine Devices", "exchange": "Nasdaq", "ambiguous": True},
        {"ticker": "ALP", "cik": "0000001002", "title": "Alpine Holdings", "exchange": "NYSE", "ambiguous": True},
        {"ticker": "AMIN", "cik": "0000001003", "title": "Alpine Mining", "ambiguous": False},
    ]


def test_exact_ticker_ranks_first_and_result_never_exceeds_twenty() -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    rows = [[1000 + index, f"ALP Corp {index}", f"A{index}", "Nasdaq"] for index in range(30)]
    rows.append([9999, "Unrelated Name", "ALP", "NYSE"])
    result = search_sec_company_candidates(
        "alp",
        user_agent="Research Tool contact@example.com",
        fetcher=lambda _url, _agent: (_payload(rows), {}),
        limit=500,
    )

    assert result["status"] == "ready"
    assert len(result["candidates"]) == 20
    assert result["candidates"][0]["ticker"] == "ALP"


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (b'{"fields":["name","cik","ticker","exchange"],"data":[]}', "sec_map_schema_invalid"),
        (b'{"fields":["cik","name","ticker","exchange"],"data":[[1,"X","X"]]}', "sec_map_row_invalid"),
        (b'{"fields":[],"fields":[],"data":[]}', "json_duplicate_key"),
    ],
)
def test_malformed_official_payload_is_unavailable(raw: bytes, reason: str) -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    result = search_sec_company_candidates(
        "x",
        user_agent="Research Tool contact@example.com",
        fetcher=lambda _url, _agent: (raw, {}),
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == reason
    assert result["candidates"] == []


@pytest.mark.parametrize(("query", "agent", "reason"), [
    ("", "Research Tool contact@example.com", "invalid_query"),
    ("x" * 121, "Research Tool contact@example.com", "invalid_query"),
    ("NVDA", None, "sec_user_agent_required"),
])
def test_invalid_request_does_not_contact_sec(query: str, agent: str | None, reason: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    monkeypatch.delenv("SEC_USER_AGENT", raising=False)

    def should_not_fetch(_url: str, _agent: str) -> tuple[bytes, dict[str, str]]:
        pytest.fail("SEC fetch should not be called")

    result = search_sec_company_candidates(query, user_agent=agent, fetcher=should_not_fetch)
    assert result["status"] == "unavailable"
    assert result["reason"] == reason
    assert result["candidates"] == []


def test_fetch_protocol_error_does_not_expose_exception_text() -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    def failed_fetch(_url: str, _agent: str) -> tuple[bytes, dict[str, str]]:
        raise ValueError("upstream response contained private diagnostic")

    result = search_sec_company_candidates(
        "NVDA",
        user_agent="Research Tool contact@example.com",
        fetcher=failed_fetch,
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "sec_fetch_unavailable"
    assert result["candidates"] == []
    assert "private diagnostic" not in str(result)


def test_redirected_response_is_not_accepted_as_official_sec_source(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.providers import sec_company_discovery as discovery

    class RedirectedResponse:
        headers = {"Last-Modified": "Thu, 29 Oct 2026 14:00:00 GMT"}

        def __enter__(self):
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def geturl(self) -> str:
            return "https://untrusted.example/company_tickers_exchange.json"

        def read(self, _maximum: int) -> bytes:
            return _payload([[1045810, "NVIDIA CORPORATION", "NVDA", "Nasdaq"]])

    monkeypatch.setattr(discovery, "urlopen", lambda _request, timeout: RedirectedResponse())
    result = discovery.search_sec_company_candidates(
        "NVDA",
        user_agent="Research Tool contact@example.com",
        observed_at=datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc),
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "sec_fetch_unavailable"
    assert result["candidates"] == []


def test_nonstring_identifying_agent_is_rejected_before_fetch() -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    result = search_sec_company_candidates(
        "NVDA",
        user_agent=1234,  # type: ignore[arg-type]
        fetcher=lambda _url, _agent: pytest.fail("fetch must not run"),
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "sec_user_agent_required"


def test_unusable_cik_does_not_become_an_openable_company_candidate() -> None:
    from src.providers.sec_company_discovery import search_sec_company_candidates

    result = search_sec_company_candidates(
        "X",
        user_agent="Research Tool contact@example.com",
        fetcher=lambda _url, _agent: (_payload([[10000000000, "Example", "X", "Nasdaq"]]), {}),
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "sec_map_row_invalid"
    assert result["candidates"] == []
