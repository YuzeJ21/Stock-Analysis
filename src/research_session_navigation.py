"""Keep the Workbench–Monitor detour within the existing Streamlit session."""

from dataclasses import dataclass

from src.dashboard_navigation import RESEARCH_MODE, company_workbench_query
from src.online_company_search import online_company_candidate_for_route


_ORIGIN_KEY = "research_monitor_origin"


@dataclass(frozen=True)
class MonitorOrigin:
    profile_key: str
    ticker: str
    section: str
    online_cik: str | None


def open_research_monitor(st, ticker: str, profile_key: str) -> None:
    """Capture the selected route before the Workbench's section widget is removed."""
    online = st.query_params.get("online") == "1"
    candidate = online_company_candidate_for_route(ticker, st.session_state) if online else None
    query = {"mode": RESEARCH_MODE, "page": "monitor"}
    if online and candidate is None:
        st.session_state.pop(_ORIGIN_KEY, None)
    else:
        st.session_state[_ORIGIN_KEY] = MonitorOrigin(
            profile_key, ticker, st.query_params.get("section", "overview"),
            candidate["cik"] if candidate else None,
        )
        query["return_ticker"] = ticker
    st.query_params.from_dict(query)


def research_monitor_origin(state, profile_key: str, ticker: str) -> MonitorOrigin | None:
    """Allow an online-only return only for this session's verified company and profile."""
    origin = state.get(_ORIGIN_KEY)
    if not isinstance(origin, MonitorOrigin) or origin.profile_key != profile_key or origin.ticker != ticker:
        return None
    if origin.online_cik is not None:
        candidate = online_company_candidate_for_route(ticker, state)
        if candidate is None or candidate["cik"] != origin.online_cik:
            return None
    return origin


def open_research_company(st, ticker: str, *, online: bool = False, section: str = "", expected_cik: str | None = None) -> None:
    if expected_cik is not None:
        candidate = online_company_candidate_for_route(ticker, st.session_state)
        if candidate is None or candidate["cik"] != expected_cik:
            return
    st.query_params.from_dict(company_workbench_query(ticker, online=online, section=section))


# Streamlit's widget callback preserves its WebSocket. Keep the navigation anchors
# usable as ordinary deep links for modified clicks and when the widget is unavailable.
RESEARCH_NAVIGATION_BRIDGE = """<style>
.st-key-research-nav-monitor, .st-key-research-nav-workbench,
.st-key-research-online-navigation {display:none!important;}
</style>
<script>
(() => {
  if (window.__stockResearchMonitorNavigation) return;
  window.__stockResearchMonitorNavigation = true;
  document.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const link = event.target?.closest?.('nav.research-workflow-navigation a[data-research-session-route], .online-company-results a[data-research-session-route]');
    const route = link?.dataset.researchSessionRoute;
    const company = link?.dataset.researchCompanyToken;
    const selector = route === 'monitor' ? '.st-key-research-nav-monitor button'
      : route === 'workbench' ? '.st-key-research-nav-workbench button'
      : route === 'online-company' && /^[0-9a-f]{2,42}-[0-9]{10}$/.test(company)
        ? '.st-key-research-online-navigation .st-key-research-nav-company-' + company + ' button' : null;
    const button = selector && document.querySelector(selector);
    if (!button || button.disabled) return;
    event.preventDefault();
    button.click();
  });
})();
</script>"""
