"""Run the local dashboard under one fixed, synthetic profile per server."""

from dataclasses import replace
from functools import lru_cache
import socket

from pytest import MonkeyPatch


@lru_cache(maxsize=1)
def _configure(store, profile, unexpected_requests):
    from src import (
        company_research_notes,
        company_workbench_ui,
        dashboard,
        online_company_identity,
        online_company_prices,
        online_research_context_store,
        online_research_tools_ui,
        sec_annual_history,
        sec_research_review_ui,
    )

    build_profile = dashboard.build_profile_context
    read_peers = company_workbench_ui.get_online_peer_valuation

    def reject(*args, **kwargs):
        with unexpected_requests.open("a", encoding="utf-8") as log:
            log.write("Unexpected provider acquisition\n")
        raise AssertionError("This local replay rehearsal allows no provider requests")

    def loopback_only(connect):
        def wrapped(sock, address):
            if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
                reject()
            return connect(sock, address)
        return wrapped

    def peers(ticker, state, *, refresh_requested, **kwargs):
        if refresh_requested:
            return reject()
        return read_peers(ticker, state, refresh_requested=False, **kwargs)

    # Hooks last for the owned subprocess, including callbacks and overlapping
    # Streamlit script runs after a top-level navigation.
    patch = MonkeyPatch()
    for module in (company_research_notes, online_research_context_store,
                   online_research_tools_ui, sec_research_review_ui):
        patch.setattr(module, "PROJECT_ROOT", store)
    patch.setattr(dashboard, "build_profile_context",
                  lambda *args, **kwargs: replace(build_profile(*args, **kwargs), profile_key=profile))
    patch.setattr(socket.socket, "connect", loopback_only(socket.socket.connect))
    patch.setattr(socket.socket, "connect_ex", loopback_only(socket.socket.connect_ex))
    patch.setattr(dashboard, "search_sec_company_candidates", reject)
    patch.setattr(sec_annual_history, "fetch_sec_online_research_view", reject)
    patch.setattr(online_company_prices, "fetch_online_company_prices", reject)
    patch.setattr(online_company_identity, "fetch_sec_company_profile", reject)
    patch.setattr(company_workbench_ui, "get_online_peer_valuation", peers)
    return dashboard.main


def run(store, profile, unexpected_requests):
    _configure(store, profile, unexpected_requests)()
