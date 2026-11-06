"""Synthetic tests for the narrow SEC venue reconciliation."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import socket

import pytest

from test_online_peer_valuation import digest


NOW = datetime(2026, 11, 6, 3, 50, tzinfo=timezone.utc)
STAMP = "2026-11-06T03:50:00Z"
CASES = (
    ("BKTI", "0000002186", dict(form="8-K", reportDate="2026-10-08", filingDate="2026-10-13",
        acceptanceDateTime="2026-10-13T11:15:08.000Z", accessionNumber="0001437749-26-032498",
        primaryDocument="bkti20261012_8k.htm", isInlineXBRL=1, isXBRL=1), "Common Stock , par value $0.60 per share"),
    ("UMAC", "0001956955", dict(form="10-Q", reportDate="2026-09-30", filingDate="2026-11-05",
        acceptanceDateTime="2026-11-05T21:07:09.000Z", accessionNumber="0001683168-26-008349",
        primaryDocument="umac_i10q-093026.htm", isInlineXBRL=1, isXBRL=1), "Common Stock, par value $0.01 per share"),
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _profile(ticker, cik, records):
    payload = dict(cik=cik, tickers=[ticker], exchanges=["NYSE"],
                   filings={"recent": {key: [r[key] for r in records] for key in records[0]}})
    return dict(status="ready", source_url=f"https://data.sec.gov/submissions/CIK{cik}.json",
                observed_at=STAMP, payload=payload, payload_sha256=digest(payload),
                normalized_sha256=digest(payload))


def _body(ticker, title, venue="NYSE American"):
    return (
        "<html><body><table><tr><th>Title of each class</th><th>Trading Symbol(s)</th>"
        "<th>Name of each exchange on which registered</th></tr>"
        f"<tr><td>{title}</td><td>{ticker}</td><td>{venue}</td></tr></table></body></html>"
    ).encode()


@pytest.fixture(params=CASES, ids=["bkti", "umac"])
def venue(request, monkeypatch):
    from src import online_peer_sec_venue as helper

    def unexpected_network(*args, **kwargs):
        pytest.fail("Synthetic listing cover proof attempted a live connection")

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    monkeypatch.setattr(socket.socket, "connect", unexpected_network)
    ticker, cik, filing, title = request.param
    scope = helper._SCOPES[ticker, cik]
    body = _body(ticker, title)
    raw = body.replace(b"</body>", b'<script type="text/javascript" src="/fixture/tail"></script></body>')
    monkeypatch.setitem(helper._SCOPES, (ticker, cik), replace(scope, body_sha256=_sha(body)))
    profile = _profile(ticker, cik, [filing])
    url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
           f"{filing['accessionNumber'].replace('-', '')}/{filing['primaryDocument']}")
    calls = []

    def source(requested, agent):
        calls.append(requested)
        return raw, {}, requested

    def fetch(**kwargs):
        options = dict(user_agent="Synthetic test contact", fetcher=source, observed_at=NOW)
        options.update(kwargs)
        return helper.fetch_listing_venue_evidence(
            options.pop("ticker", ticker), options.pop("cik", cik), options.pop("profile", profile), **options
        )

    def validate(packet, *, as_of=NOW):
        return helper.validated_listing_venue_evidence(packet, ticker=ticker, cik=cik, profile=profile, as_of=as_of)

    return dict(helper=helper, ticker=ticker, cik=cik, profile=profile, url=url, body=body, raw=raw,
                title=title, filing=filing, calls=calls, fetch=fetch, validate=validate)


def test_exact_common_cover_reconciles_the_raw_profile_label_without_storing_html(venue):
    ticker, cik = venue["ticker"], venue["cik"]
    assert venue["helper"].known_listing_venue_scope(ticker, cik)
    assert not venue["helper"].known_listing_venue_scope("OTHER", cik)
    before = deepcopy(venue["profile"])
    packet = venue["fetch"]()
    assert packet["status"] == "observed"
    assert "Synthetic" not in str(packet) and "<html" not in str(packet)
    assert "payload_raw_base64" not in str(packet)
    evidence = venue["validate"](packet)
    filing = venue["filing"]
    assert evidence == dict(source_url=venue["url"], observed_at=STAMP, payload_sha256=_sha(venue["raw"]),
        body_sha256=_sha(venue["body"]), accession=filing["accessionNumber"], form=filing["form"],
        filed=filing["filingDate"], reported_exchange="NYSE", confirmed_exchange="NYSE American")
    assert venue["profile"] == before and venue["calls"] == [venue["url"]]


@pytest.mark.parametrize("change", ["ticker", "cik", "profile_cik", "already_american", "extra_security", "changed_metadata", "stale"])
def test_nonmatching_profile_scope_does_not_request_a_cover(venue, change):
    profile = venue["profile"]
    kwargs = {}
    if change == "ticker":
        kwargs["ticker"] = "OTHER"
    elif change == "cik":
        kwargs["cik"] = "0000001001"
    elif change == "profile_cik":
        profile["payload"]["cik"] = "0000001001"
    elif change == "already_american":
        profile["payload"]["exchanges"] = ["NYSE American"]
    elif change == "extra_security":
        profile["payload"]["tickers"].append("OTHER")
        profile["payload"]["exchanges"].append("NYSE")
    elif change == "changed_metadata":
        profile["payload"]["filings"]["recent"]["primaryDocument"] = ["other.htm"]
    else:
        profile["observed_at"] = "2026-11-04T03:50:00Z"
    profile["normalized_sha256"] = digest(profile["payload"])
    assert venue["fetch"](**kwargs)["status"] != "observed"
    assert venue["calls"] == []


@pytest.mark.parametrize("form", ["8-K", "10-Q/A", "8-A12B", "CERT", "25-NSE"])
def test_newer_relevant_filing_withholds_the_old_review_without_a_request(venue, form):
    newer = dict(venue["filing"], form=form, reportDate="", filingDate="2026-11-06",
                 acceptanceDateTime="2026-11-06T00:00:00Z",
                 accessionNumber="0000001001-26-000002", primaryDocument="new.htm")
    profile = _profile(venue["ticker"], venue["cik"], [venue["filing"], newer])
    assert venue["fetch"](profile=profile)["status"] != "observed"
    assert venue["calls"] == []


@pytest.mark.parametrize("change", ["redirect", "body", "empty", "unavailable", "wrong_visible_ticker", "wrong_visible_venue"])
def test_cover_must_match_both_the_bound_body_and_visible_security_grid(venue, monkeypatch, change):
    def fetcher(url, agent):
        venue["calls"].append(url)
        if change == "redirect":
            return venue["raw"], {}, url + "?redirect"
        if change == "body":
            return venue["raw"] + b" ", {}, url
        if change == "empty":
            return b"", {}, url
        if change == "unavailable":
            raise OSError("Synthetic source unavailable")
        raw = (_body("OTHER", venue["title"]) if change == "wrong_visible_ticker"
               else _body(venue["ticker"], venue["title"], "New York Stock Exchange"))
        key = venue["ticker"], venue["cik"]
        scopes = venue["helper"]._SCOPES
        monkeypatch.setitem(scopes, key, replace(scopes[key], body_sha256=_sha(raw)))
        return raw, {}, url

    packet = venue["fetch"](fetcher=fetcher)
    assert packet["status"] != "observed" and venue["validate"](packet) is None
    assert venue["calls"] == [venue["url"]]


def test_replay_needs_fresh_evidence_and_the_original_profile_digest(venue):
    packet = venue["fetch"]()
    assert venue["validate"](packet)
    assert venue["validate"](packet, as_of=NOW + timedelta(hours=24, seconds=1)) is None
    venue["profile"]["payload_sha256"] = "a" * 64
    assert venue["validate"](packet) is None
    assert venue["calls"] == [venue["url"]]


def test_document_receipt_cannot_precede_the_exact_filings_acceptance(venue):
    packet = venue["fetch"]()
    accepted = datetime.fromisoformat(venue["filing"]["acceptanceDateTime"].replace("Z", "+00:00"))
    before = accepted - timedelta(seconds=1)
    as_of = accepted + timedelta(hours=1)
    venue["profile"]["observed_at"] = as_of.isoformat()
    packet["document"]["observed_at"] = before.isoformat()
    packet["packet_digest"] = venue["helper"]._seal(packet)
    assert venue["validate"](packet, as_of=as_of) is None


@pytest.mark.parametrize("failure", ["transport", "scope"])
def test_collector_distinguishes_cover_access_failure_from_unverified_venue(venue, failure):
    from src.online_peer_coverage import _subject_source_failure
    from src.online_peer_sources import _collect_issuer

    def read_cover(*args, **kwargs):
        if failure == "transport":
            raise OSError("Synthetic SEC access failure")
        return dict(status="unavailable", reason="listing_venue_scope_unverified")

    ticker, cik = venue["ticker"], venue["cik"]
    facts = dict(status="ready", payload=dict(cik=cik, facts={}))
    deps = dict(sec=lambda url, **kwargs: venue["profile"] if "/submissions/" in url else facts,
                prices=lambda *args, **kwargs: dict(status="inspection_only", exchange_code="ASE",
                                                    full_exchange_name="NYSE American"),
                venue=read_cover, history=lambda *args, **kwargs: dict(status="not_applicable"))
    vendor = dict(status="observed", payload=dict(info=dict(quoteType="EQUITY", exchange="ASE",
                                                          fullExchangeName="NYSE American")))
    row = _collect_issuer(ticker, cik, deps, "Synthetic contact", NOW, vendor)
    is_access_failure = failure == "transport"
    assert (row.get("reason") == "listing_venue_source_unavailable") is is_access_failure
    assert _subject_source_failure(dict(ticker=ticker), dict(collection=dict(issuers=[row]))) is is_access_failure


def test_restricted_modes_do_not_collect_or_replay_venue_evidence(venue, monkeypatch):
    packet = venue["fetch"]()
    assert packet["status"] == "observed"
    assert venue["fetch"](workspace_mode="public")["status"] != "observed"
    monkeypatch.setenv("COMMERCIAL_RESEARCH_MODE", "1")
    assert venue["fetch"]()["status"] != "observed"
    assert venue["validate"](packet) is None
    assert venue["calls"] == [venue["url"]]
