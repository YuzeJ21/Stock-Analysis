"""The SO co-filing proof binds one vendor link to two exact SEC sources."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import socket

import pytest

from test_online_peer_valuation import digest


NOW = datetime(2026, 11, 6, 3, 30, tzinfo=timezone.utc)
STAMP = "2026-11-06T03:30:00Z"
PARENT = "0000092122"
CO_REGISTRANT = "0001160661"
CO_PROFILE_URL = "https://data.sec.gov/submissions/CIK0001160661.json"
PARENT_PROFILE_URL = "https://data.sec.gov/submissions/CIK0000092122.json"
ARCHIVE_URLS = (
    "https://www.sec.gov/Archives/edgar/data/92122/000009212225000084/so-20250930.htm",
    "https://www.sec.gov/Archives/edgar/data/1160661/000009212225000084/so-20250930.htm",
)
VENDOR_LINK = "https://finance.yahoo.com/sec-filing/SO/0000092122-25-000084_92122"
VENDOR_EXHIBIT = "https://cdn.yahoofinance.com/prod/sec-filings/0001160661/000009212225000084/so-20250930.htm"
FILING = dict(
    form="10-Q", reportDate="2025-09-30", filingDate="2025-10-30",
    acceptanceDateTime="2025-10-29T21:40:57.000Z", accessionNumber="0000092122-25-000084",
    primaryDocument="so-20250930.htm", isInlineXBRL=1, isXBRL=1,
)
ANNUAL = dict(
    form="10-K", reportDate="2025-12-31", filingDate="2026-02-19",
    acceptanceDateTime="2026-02-18T22:46:14.000Z", accessionNumber="0000092122-26-000006",
    primaryDocument="so-20251231.htm", isInlineXBRL=1, isXBRL=1,
)
BODY = b"<html><body><p>Synthetic shared filing.</p></body></html>"


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _decorated_body(route):
    script = f'<script type="text/javascript" src="/fixture/{route}"></script>'.encode()
    return BODY.replace(b"</body>", script + b"</body>")


def _profile_payload(cik, name, tickers, filings):
    return dict(cik=cik, name=name, tickers=tickers, exchanges=["NYSE"] * len(tickers), filings={
        "recent": {key: [filing[key] for filing in filings] for key in FILING},
        "files": [],
    })


@pytest.fixture
def cofiling(monkeypatch):
    from src import online_peer_sec_cofiling as helper

    def unexpected_network(*args, **kwargs):
        pytest.fail("Synthetic co-filing proof attempted a live network request")

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    monkeypatch.setattr(socket.socket, "connect", unexpected_network)
    monkeypatch.setattr(helper, "BODY_SHA256", _sha(BODY))
    parent_payload = _profile_payload(PARENT, "Synthetic Parent", ["SO"], [ANNUAL, FILING])
    co_payload = _profile_payload(CO_REGISTRANT, "Synthetic Co-registrant", [], [FILING])
    profile = dict(status="ready", source_url=PARENT_PROFILE_URL, observed_at=STAMP,
                   payload=parent_payload, payload_sha256=digest(parent_payload),
                   normalized_sha256=digest(parent_payload))
    vendor_payload = {
        "info": {"symbol": "SO", "quoteType": "EQUITY"},
        "filings": [{"type": "10-Q", "date": "2025-10-30", "edgarUrl": VENDOR_LINK,
                     "exhibits": {"10-Q": VENDOR_EXHIBIT}}],
    }
    vendor = dict(status="observed", source_ref="https://finance.yahoo.com/quote/SO/",
                  observed_at=STAMP, adapter="yfinance_public_methods", adapter_version="synthetic",
                  payload=vendor_payload, normalized_sha256=digest(vendor_payload))
    documents = dict(zip(ARCHIVE_URLS, (_decorated_body("parent"), _decorated_body("coregistrant"))))
    calls = []

    def sec_fetcher(url, agent):
        calls.append(url)
        assert url == CO_PROFILE_URL
        return json.dumps(co_payload).encode(), {}, url

    def html_fetcher(url, agent):
        calls.append(url)
        return documents[url], {}, url

    def fetch(**kwargs):
        options = dict(user_agent="Synthetic test contact", observed_at=NOW,
                       fetcher=sec_fetcher, html_fetcher=html_fetcher)
        options.update(kwargs)
        cik = options.pop("cik", PARENT)
        return helper.fetch_vendor_cofiling_match(cik, profile, vendor, **options)

    def validate(packet, *, as_of=NOW):
        return helper.validated_vendor_cofiling_match(
            packet, cik=PARENT, profile=profile, vendor=vendor, as_of=as_of
        )

    return dict(fetch=fetch, validate=validate, profile=profile, co_payload=co_payload,
                vendor=vendor, documents=documents, calls=calls)


def test_single_exact_cofiling_preserves_two_receipts_without_changing_annual_inputs(cofiling):
    before = deepcopy(cofiling["profile"])
    packet = cofiling["fetch"]()
    assert packet["status"] == "observed"
    evidence = cofiling["validate"](packet)

    assert evidence["source_ref"] == VENDOR_LINK
    assert evidence["accession"] == FILING["accessionNumber"]
    assert evidence["filed"] == FILING["filingDate"]
    assert evidence["co_registrant_source_ref"] == CO_PROFILE_URL
    assert evidence["financial_denominator_modified"] is False
    documents = evidence["cofiling_documents"]
    assert [row["source_url"] for row in documents] == list(ARCHIVE_URLS)
    assert {row["body_sha256"] for row in documents} == {_sha(BODY)}
    assert [row["payload_sha256"] for row in documents] == [
        _sha(cofiling["documents"][url]) for url in ARCHIVE_URLS
    ]
    assert cofiling["profile"] == before
    assert cofiling["calls"] == [CO_PROFILE_URL, *ARCHIVE_URLS]


@pytest.mark.parametrize("change", ["ticker", "cik", "vendor_cik", "accession", "form", "date", "filename", "host", "extra_query"])
def test_wrong_scope_stops_before_any_sec_request(cofiling, change):
    vendor = cofiling["vendor"]
    filing = vendor["payload"]["filings"][0]
    kwargs = {}
    if change == "ticker":
        vendor["payload"]["info"]["symbol"] = "NEE"
        vendor["source_ref"] = vendor["source_ref"].replace("/SO/", "/NEE/")
    elif change == "cik":
        kwargs["cik"] = CO_REGISTRANT
    elif change == "vendor_cik":
        filing["edgarUrl"] = VENDOR_LINK.replace("_92122", "_1160661")
    elif change == "accession":
        filing["edgarUrl"] = VENDOR_LINK.replace("-000084_", "-000085_")
    elif change == "form":
        filing.update(type="10-K", exhibits={"10-K": VENDOR_EXHIBIT})
    elif change == "date":
        filing["date"] = "2025-10-31"
    elif change == "filename":
        filing["exhibits"]["10-Q"] = VENDOR_EXHIBIT.replace("so-20250930.htm", "another.htm")
    elif change == "host":
        filing["exhibits"]["10-Q"] = VENDOR_EXHIBIT.replace("cdn.yahoofinance.com", "www.sec.gov")
    else:
        filing["exhibits"]["10-Q"] = VENDOR_EXHIBIT + "?download=1"
    vendor["normalized_sha256"] = digest(vendor["payload"])

    assert cofiling["fetch"](**kwargs)["status"] != "observed"
    assert cofiling["calls"] == []


@pytest.mark.parametrize("change", ["direct_parent_exhibit", "stale_parent", "stale_vendor"])
def test_ordinary_parent_match_or_stale_input_does_not_trigger_cofiling_fetch(cofiling, change):
    vendor = cofiling["vendor"]
    if change == "direct_parent_exhibit":
        vendor["payload"]["filings"][0]["exhibits"]["10-Q"] = VENDOR_EXHIBIT.replace(CO_REGISTRANT, PARENT)
        vendor["normalized_sha256"] = digest(vendor["payload"])
    else:
        target = vendor if change == "stale_vendor" else cofiling["profile"]
        target["observed_at"] = "2026-11-04T03:30:00Z"

    assert cofiling["fetch"]()["status"] != "observed"
    assert cofiling["calls"] == []


@pytest.mark.parametrize("change", ["wrong_cik", "wrong_date", "missing_filing"])
def test_wrong_co_registrant_metadata_stops_before_archive_requests(cofiling, change):
    co_payload = cofiling["co_payload"]
    if change == "wrong_cik":
        co_payload["cik"] = PARENT
    elif change == "wrong_date":
        co_payload["filings"]["recent"]["filingDate"] = ["2025-10-31"]
    else:
        co_payload["filings"]["recent"] = {key: [] for key in FILING}

    assert cofiling["fetch"]()["status"] != "observed"
    assert cofiling["calls"] == [CO_PROFILE_URL]


@pytest.mark.parametrize("change", ["changed_body", "redirect", "empty", "unavailable"])
def test_unverified_exact_archive_body_is_withheld_without_a_retry(cofiling, change):
    def response(url, agent):
        cofiling["calls"].append(url)
        raw = cofiling["documents"][url]
        if url == ARCHIVE_URLS[1]:
            if change == "changed_body":
                raw = raw.replace(b"Synthetic", b"Changed")
            elif change == "redirect":
                return raw, {}, ARCHIVE_URLS[0]
            elif change == "empty":
                raw = b""
            else:
                raise OSError("Synthetic source unavailable")
        return raw, {}, url

    packet = cofiling["fetch"](html_fetcher=response)

    assert packet["status"] != "observed"
    assert cofiling["validate"](packet) is None
    assert cofiling["calls"] == [CO_PROFILE_URL, *ARCHIVE_URLS]


@pytest.mark.parametrize("change", ["body_digest", "co_profile", "parent_digest", "vendor_target", "stale"])
def test_replay_revalidates_current_scope_and_dated_proof_without_requests(cofiling, change):
    packet = cofiling["fetch"]()
    assert packet["status"] == "observed"
    now = NOW
    if change == "body_digest":
        packet["documents"][1]["body_sha256"] = "a" * 64
        packet["packet_digest"] = digest({key: value for key, value in packet.items() if key != "packet_digest"})
    elif change == "co_profile":
        packet["co_registrant"]["payload"]["cik"] = PARENT
        packet["packet_digest"] = digest({key: value for key, value in packet.items() if key != "packet_digest"})
    elif change == "parent_digest":
        cofiling["profile"]["payload_sha256"] = "a" * 64
    elif change == "vendor_target":
        vendor = cofiling["vendor"]
        vendor["payload"]["filings"][0]["exhibits"]["10-Q"] += "?other=1"
        vendor["normalized_sha256"] = digest(vendor["payload"])
    else:
        now += timedelta(hours=24, seconds=1)
        fresh = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        cofiling["profile"]["observed_at"] = cofiling["vendor"]["observed_at"] = fresh
    before = list(cofiling["calls"])

    assert cofiling["validate"](packet, as_of=now) is None
    assert cofiling["calls"] == before


def test_nonpersonal_mode_blocks_fetch_and_commercial_mode_blocks_replay(cofiling, monkeypatch):
    packet = cofiling["fetch"]()
    assert packet["status"] == "observed"
    before = list(cofiling["calls"])
    assert cofiling["fetch"](workspace_mode="public")["status"] != "observed"
    monkeypatch.setenv("COMMERCIAL_RESEARCH_MODE", "1")
    assert cofiling["fetch"]()["status"] != "observed"
    assert cofiling["validate"](packet) is None
    assert cofiling["calls"] == before
