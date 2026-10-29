"""Pure presentation primitives shared by dashboard integrations."""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit


_VISUAL_TOKENS = {
    "--sr-canvas": "#F6F7F4",
    "--sr-surface": "#FFFFFF",
    "--sr-surface-muted": "#F1F4F1",
    "--sr-ink": "#0F172A",
    "--sr-text": "#243244",
    "--sr-muted": "#475569",
    "--sr-border": "#D9E1DC",
    "--sr-nav": "#0B1B2B",
    "--sr-nav-text": "#F8FAFC",
    "--sr-nav-muted": "#CBD5E1",
    "--sr-forest": "#155E4B",
    "--sr-teal": "#0F766E",
    "--sr-amber": "#854D0E",
    "--sr-red": "#B42318",
    "--sr-blue": "#315D8A",
    "--sr-focus": "#0B6BFF",
}

_CANONICAL_ROUTE_KEYS = frozenset(
    {
        "mode",
        "page",
        "ticker",
        "open",
        "cash_preview",
        "lane",
        "drawer",
        "queue_details",
        "batch_details",
        "proof_details",
        "metric_details",
    }
)


_HTML_FRAGMENT_PROVENANCE = object()


@dataclass(frozen=True, init=False)
class HtmlFragment:
    value: str

    def __init__(self, value: str) -> None:
        del value
        raise TypeError(
            "HtmlFragment values are created by module presentation helpers only."
        )


@dataclass(frozen=True)
class SafeRouteAction:
    label: str
    href: str
    aria_label: str | None = None

    def __post_init__(self) -> None:
        _validate_safe_route_href(self.href)


@dataclass(frozen=True)
class EvidenceRow:
    lane: str
    role: str
    state: str
    count_or_cutoff: str
    reason: str
    display_label: str | None = None
    evidence_action: SafeRouteAction | None = None


@dataclass(frozen=True)
class TimelineRecord:
    record_id: str
    timestamp: str | None
    label: str
    summary: str
    evidence_action: SafeRouteAction | None = None


@dataclass(frozen=True)
class VisualState:
    role: str
    state: str
    semantic: str
    label: str
    foreground: str
    background: str
    border: str


def visual_tokens() -> dict[str, str]:
    """Return a copy of the approved calm institutional token palette."""

    return dict(_VISUAL_TOKENS)


def _normalized_label(state: str, label: str | None) -> str:
    explicit = str(label or "").strip()
    if explicit:
        return explicit
    normalized = str(state or "").strip()
    return normalized if normalized else "Unknown"


def visual_state(role: str, state: str, label: str | None = None) -> VisualState:
    """Map an explicit semantic role and state without inferring investment sentiment."""

    normalized_role = str(role or "").strip().casefold()
    normalized_state = re.sub(
        r"[^a-z0-9]+",
        "_",
        str(state or "").strip().casefold(),
    ).strip("_")
    semantic = "neutral"
    foreground = _VISUAL_TOKENS["--sr-muted"]
    if normalized_role in {"evidence", "readiness"}:
        if normalized_state in {
            "supported",
            "ready",
            "usable_now",
            "research_ready",
            "available",
            "valid",
            "liquid",
            "low_co_movement",
        }:
            semantic, foreground = "supported", _VISUAL_TOKENS["--sr-teal"]
        elif normalized_state in {
            "partial",
            "waiting",
            "candidate_context_only",
            "partial_coverage",
            "valid_with_warnings",
            "moderate_liquidity",
            "moderate_co_movement",
        }:
            semantic, foreground = "partial", _VISUAL_TOKENS["--sr-amber"]
        elif normalized_state in {
            "blocked",
            "missing",
            "unavailable",
            "needs_price_data",
            "needs_enrichment",
            "missing_file",
            "not_available",
            "peer_data_unavailable",
            "insufficient_peer_data",
            "insufficient_price_data",
            "thin_needs_review",
            "high_co_movement",
            "insufficient_overlap",
            "insufficient_data",
        }:
            semantic, foreground = "blocked", _VISUAL_TOKENS["--sr-red"]
        elif normalized_state == "stale":
            semantic, foreground = "stale", _VISUAL_TOKENS["--sr-amber"]
        elif normalized_state == "excluded":
            semantic, foreground = "excluded", _VISUAL_TOKENS["--sr-muted"]
        elif normalized_state == "withheld":
            semantic, foreground = "withheld", _VISUAL_TOKENS["--sr-amber"]
    elif normalized_role == "freshness":
        if normalized_state in {"current", "fresh", "ready"}:
            semantic, foreground = "supported", _VISUAL_TOKENS["--sr-teal"]
        elif normalized_state in {"mixed", "partial", "stale"}:
            semantic, foreground = "partial", _VISUAL_TOKENS["--sr-amber"]
        elif normalized_state in {"missing", "unavailable"}:
            semantic, foreground = "blocked", _VISUAL_TOKENS["--sr-red"]
    elif normalized_role == "workflow" and normalized_state in {
        "current",
        "primary",
        "safe_action",
    }:
        semantic, foreground = "workflow", _VISUAL_TOKENS["--sr-forest"]
    elif normalized_role == "trace" and normalized_state in {
        "source_backed",
        "traceable",
        "changed",
    }:
        semantic, foreground = "trace", _VISUAL_TOKENS["--sr-blue"]
    return VisualState(
        role=normalized_role or "unknown",
        state=normalized_state or "unknown",
        semantic=semantic,
        label=_normalized_label(state, label),
        foreground=foreground,
        background=_VISUAL_TOKENS["--sr-surface-muted"],
        border=foreground,
    )


def _validate_safe_route_href(href: str) -> None:
    value = str(href or "").strip()
    parsed = urlsplit(value)
    if (
        not value
        or not value.startswith("?")
        or value.startswith("//")
        or parsed.scheme
        or parsed.netloc
        or parsed.path
        or parsed.fragment
    ):
        raise ValueError("Safe route actions require a same-app query-only URL.")
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    keys = [key for key, _ in pairs]
    if not pairs or any(not key or key not in _CANONICAL_ROUTE_KEYS for key in keys):
        raise ValueError("Safe route actions may use canonical route keys only.")
    if len(keys) != len(set(keys)):
        raise ValueError("Safe route actions cannot repeat a controlled route key.")
    if any(not str(value).strip() for _, value in pairs):
        raise ValueError("Safe route action values cannot be empty.")
    modes = [value for key, value in pairs if key == "mode"]
    if len(modes) != 1 or modes[0] not in {"public", "research", "operator"}:
        raise ValueError("Safe route actions require one canonical workspace mode.")


def _trusted_fragment(value: str) -> HtmlFragment:
    fragment = object.__new__(HtmlFragment)
    object.__setattr__(fragment, "value", str(value))
    object.__setattr__(fragment, "_html_fragment_provenance", _HTML_FRAGMENT_PROVENANCE)
    return fragment


def _fragment(value: HtmlFragment, *, field: str) -> str:
    if (
        type(value) is not HtmlFragment
        or getattr(value, "_html_fragment_provenance", None)
        is not _HTML_FRAGMENT_PROVENANCE
    ):
        raise TypeError(f"{field} accepts trusted HtmlFragment values only.")
    return value.value


def _action_link(action: SafeRouteAction, *, region: bool) -> str:
    aria = (
        f" aria-label='{escape_attribute(action.aria_label)}'"
        if action.aria_label is not None
        else ""
    )
    region_attribute = " data-sr-region='primary-action'" if region else ""
    return (
        f"<a class='sr-primary-action public-primary-action' href='{escape_attribute(action.href)}'"
        f" target='_self'{aria}{region_attribute}>{escape_text(action.label)}</a>"
    )


def workspace_shell_html(
    *,
    mode: str,
    navigation: HtmlFragment | None,
    content: Sequence[HtmlFragment],
) -> HtmlFragment:
    navigation_html = "" if navigation is None else _fragment(navigation, field="navigation")
    content_html = "".join(_fragment(item, field="content") for item in content)
    return _trusted_fragment(
        f"<div class='sr-workspace-shell' data-sr-mode='{escape_attribute(mode)}'>"
        f"{navigation_html}<div class='sr-workspace-content'>{content_html}</div></div>"
    )


def context_bar_html(items: Sequence[tuple[str, str]]) -> HtmlFragment:
    rendered = "".join(
        "<div class='sr-context-item'>"
        f"<dt>{escape_text(label)}</dt><dd>{escape_text(value)}</dd>"
        "</div>"
        for label, value in items
    )
    return _trusted_fragment(
        "<dl class='sr-context-bar' data-sr-region='context' "
        f"aria-label='Workspace context'>{rendered}</dl>"
    )


def page_title_html(*, title: str, purpose: str) -> HtmlFragment:
    return _trusted_fragment(
        "<header class='sr-page-title' data-sr-region='page-title'>"
        f"<h1>{escape_text(title)}</h1><p>{escape_text(purpose)}</p></header>"
    )


def operator_route_shell_html(*, title: str, kind: str) -> HtmlFragment:
    """Render one neutral Operator or compatibility boundary before route detail."""

    normalized_kind = str(kind or "").strip().casefold()
    if normalized_kind not in {"operator", "compatibility"}:
        raise ValueError("Operator route shells require operator or compatibility kind.")
    if normalized_kind == "compatibility":
        kicker = "Compatibility utility"
        purpose = "Retained operator-only output for deterministic regression review."
        warning_title = "Compatibility boundary"
        warning_body = (
            "This legacy utility is excluded from Personal Research Mode and product "
            "conclusions. Analytic labels stay neutral and do not create a recommendation "
            "or transaction direction."
        )
    else:
        kicker = "Operator workspace"
        purpose = "Saved local readiness, maintenance, and review controls."
        warning_title = "Operator boundary"
        warning_body = (
            "This route preserves local controls and evidence context. It does not create "
            "a recommendation, ranking for action, or account action."
        )
    return _trusted_fragment(
        "<section class='sr-operator-route-shell' data-sr-region='operator-shell' "
        f"data-sr-operator-kind='{escape_attribute(normalized_kind)}'>"
        "<header class='sr-operator-route-title' data-sr-region='page-title'>"
        f"<p>{escape_text(kicker)}</p><h1>{escape_text(title)}</h1>"
        f"<span>{escape_text(purpose)}</span></header>"
        "<div class='sr-operator-warning' data-sr-region='operator-warning' role='note' "
        f"data-sr-operator-kind='{escape_attribute(normalized_kind)}'>"
        f"<strong>{escape_text(warning_title)}</strong>"
        f"<span>{escape_text(warning_body)}</span></div></section>"
    )


def answer_panel_html(
    *,
    question: str,
    answer: str,
    reason: str,
    action: SafeRouteAction | None,
    stop_rule: str | None,
) -> HtmlFragment:
    action_html = _action_link(action, region=True) if action is not None else ""
    stop_html = (
        "<p class='sr-stop-rule research-workspace-boundary' data-sr-region='stop-rule'>"
        f"<strong>Research boundary</strong><span>{escape_text(stop_rule)}</span></p>"
        if stop_rule
        else ""
    )
    return _trusted_fragment(
        "<section class='sr-answer-panel' data-sr-region='primary-answer' "
        "aria-label='Primary research answer'>"
        f"<p class='sr-answer-question'>{escape_text(question)}</p>"
        f"<h2>{escape_text(answer)}</h2>"
        f"<p class='sr-answer-reason'>{escape_text(reason)}</p>"
        f"{action_html}{stop_html}</section>"
    )


def status_chip_html(*, role: str, state: str, label: str | None = None) -> HtmlFragment:
    visual = visual_state(role, state, label)
    return _trusted_fragment(
        f"<span class='sr-status-chip sr-status-{escape_attribute(visual.semantic)}' "
        f"data-sr-semantic='{escape_attribute(visual.semantic)}' "
        f"style='--sr-state-fg:{escape_attribute(visual.foreground)};"
        f"--sr-state-bg:{escape_attribute(visual.background)};"
        f"--sr-state-border:{escape_attribute(visual.border)}'>"
        f"{escape_text(visual.label)}</span>"
    )


def evidence_rows_html(rows: Sequence[EvidenceRow]) -> HtmlFragment:
    rendered: list[str] = []
    for row in rows:
        chip = status_chip_html(
            role=row.role,
            state=row.state,
            label=row.display_label,
        ).value
        action = _action_link(row.evidence_action, region=False) if row.evidence_action else ""
        rendered.append(
            "<li class='sr-evidence-row'>"
            f"<div class='sr-evidence-lane'><strong>{escape_text(row.lane)}</strong>{chip}</div>"
            f"<span class='sr-evidence-count'>{escape_text(row.count_or_cutoff)}</span>"
            f"<p>{escape_text(row.reason)}</p>{action}</li>"
        )
    if not rendered:
        rendered.append(
            "<li class='sr-evidence-row sr-evidence-empty'>"
            "No supporting saved evidence is available.</li>"
        )
    return _trusted_fragment(
        "<section class='sr-supporting-evidence' data-sr-region='supporting-evidence' "
        "aria-label='Supporting evidence'><h2>Supporting evidence</h2>"
        f"<ul>{''.join(rendered)}</ul></section>"
    )


def evidence_timeline_html(
    records: Sequence[TimelineRecord],
    *,
    empty_title: str,
    empty_body: str,
    heading: str = "What changed",
    aria_label: str = "Evidence timeline",
) -> HtmlFragment:
    """Render the supplied authoritative order without deriving a latest record."""

    rendered: list[str] = []
    for record in records:
        if type(record) is not TimelineRecord:
            raise TypeError("records accepts TimelineRecord values only.")
        timestamp = str(record.timestamp or "").strip() or "Timestamp unavailable"
        action = (
            _action_link(record.evidence_action, region=False)
            if record.evidence_action is not None
            else ""
        )
        rendered.append(
            "<li class='sr-timeline-record' "
            f"data-timeline-record-id='{escape_attribute(record.record_id)}'>"
            f"<time>{escape_text(timestamp)}</time>"
            f"<strong>{escape_text(record.label)}</strong>"
            f"<p>{escape_text(record.summary)}</p>{action}</li>"
        )
    if not rendered:
        rendered.append(
            "<li class='sr-timeline-empty'>"
            f"<strong>{escape_text(empty_title)}</strong>"
            f"<p>{escape_text(empty_body)}</p></li>"
        )
    return _trusted_fragment(
        "<section class='sr-evidence-timeline' data-sr-region='supporting-evidence' "
        f"aria-label='{escape_attribute(aria_label)}'><h2>{escape_text(heading)}</h2>"
        f"<ol>{''.join(rendered)}</ol></section>"
    )


def detail_disclosure_html(
    summary: str,
    body: Sequence[HtmlFragment],
    *,
    open_by_default: bool = False,
) -> HtmlFragment:
    """Render sealed pure detail without accepting raw trusted HTML."""

    body_html = "".join(_fragment(item, field="body") for item in body)
    open_attribute = " open" if open_by_default else ""
    return _trusted_fragment(
        f"<details class='sr-detail-disclosure' data-sr-region='advanced-detail'{open_attribute}>"
        f"<summary>{escape_text(summary)}</summary>"
        f"<div class='sr-detail-disclosure-body'>{body_html}</div></details>"
    )


def detail_item_html(*, label: str, body: str) -> HtmlFragment:
    """Build escaped prose for a sealed detail disclosure."""

    return _trusted_fragment(
        "<section class='sr-detail-item'>"
        f"<strong>{escape_text(label)}</strong><p>{escape_text(body)}</p></section>"
    )


def next_action_html(action: SafeRouteAction) -> HtmlFragment:
    return _trusted_fragment(_action_link(action, region=True))


def evidence_action_html(action: SafeRouteAction) -> HtmlFragment:
    """Render a safe evidence-access link without declaring a primary action."""

    return _trusted_fragment(_action_link(action, region=False))


def next_step_prompt_html(*, title: str, body: str) -> HtmlFragment:
    """Label an adjacent native control as the route's single next action."""

    return _trusted_fragment(
        "<section class='sr-next-step-prompt'>"
        f"<strong>{escape_text(title)}</strong><span>{escape_text(body)}</span></section>"
    )


def stop_rule_html(rule: str) -> HtmlFragment:
    return _trusted_fragment(
        "<p class='sr-stop-rule research-workspace-boundary' data-sr-region='stop-rule'>"
        f"<strong>Research boundary</strong><span>{escape_text(rule)}</span></p>"
    )


def supporting_detail_html(*, title: str, body: str) -> HtmlFragment:
    return _trusted_fragment(
        "<section class='sr-supporting-intro' data-sr-region='supporting-evidence'>"
        f"<h2>{escape_text(title)}</h2><p>{escape_text(body)}</p></section>"
    )


def empty_state_html(
    *,
    title: str,
    absence: str,
    not_proven: str,
    action: SafeRouteAction | None,
) -> HtmlFragment:
    action_html = _action_link(action, region=True) if action is not None else ""
    return _trusted_fragment(
        "<section class='sr-empty-state' data-sr-region='primary-answer'>"
        f"<h2>{escape_text(title)}</h2><p>{escape_text(absence)}</p>"
        f"<p><strong>This does not prove:</strong> {escape_text(not_proven)}</p>"
        f"{action_html}</section>"
    )


def advanced_detail_marker_html() -> HtmlFragment:
    return _trusted_fragment(
        "<div class='sr-advanced-detail-marker' data-sr-region='advanced-detail'>"
        "Advanced evidence</div>"
    )


def dashboard_visual_system_css() -> str:
    """Return the dependency-free calm institutional workspace stylesheet."""

    tokens = "\n".join(f"  {name}: {value};" for name, value in _VISUAL_TOKENS.items())
    return f"""
:root {{
{tokens}
}}
html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: var(--sr-canvas) !important;
  color: var(--sr-text) !important;
  font-family: Inter, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
}}
[data-testid="stMainBlockContainer"] {{
  max-width: 76rem !important;
}}
.sr-workspace-shell, .sr-workspace-shell *, [data-sr-region], [data-sr-region] * {{
  box-sizing: border-box;
}}
.sr-workspace-content {{
  display: grid;
  gap: 16px;
  min-width: 0;
}}
.sr-visually-hidden {{
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}}
.sr-context-bar {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  margin: 0 0 8px;
  padding: 8px 0 12px;
  border-bottom: 1px solid var(--sr-border);
}}
.sr-context-item {{ display: grid; gap: 4px; min-width: 9rem; }}
.sr-context-item dt {{ color: var(--sr-muted); font-size: .75rem; }}
.sr-context-item dd {{ margin: 0; color: var(--sr-text); font-size: .8125rem; font-weight: 650; }}
.sr-page-title {{ max-width: 65ch; margin: 0 0 16px; }}
.sr-page-title h1 {{ margin: 0; color: var(--sr-ink); font-size: 1.75rem; line-height: 1.2; }}
.sr-page-title p {{ margin: 8px 0 0; color: var(--sr-muted); font-size: .9375rem; line-height: 1.5; }}
.sr-operator-route-shell {{
  display: grid;
  gap: 12px;
  margin: 0 0 16px;
  padding: 20px 24px;
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-radius: 10px;
}}
.sr-operator-route-title {{ display: grid; gap: 6px; min-width: 0; }}
.sr-operator-route-title p {{
  margin: 0;
  color: var(--sr-muted);
  font-size: .75rem;
  font-weight: 750;
  letter-spacing: .04em;
  text-transform: uppercase;
}}
.sr-operator-route-title h1 {{
  margin: 0;
  color: var(--sr-ink);
  font-size: 1.5rem;
  line-height: 1.2;
}}
.sr-operator-route-title span {{ color: var(--sr-muted); font-size: .875rem; line-height: 1.45; }}
.sr-operator-warning {{
  display: grid;
  grid-template-columns: minmax(9rem, auto) minmax(0, 1fr);
  gap: 8px 16px;
  padding: 10px 12px;
  color: var(--sr-text);
  background: var(--sr-surface-muted);
  border-left: 3px solid var(--sr-blue);
  border-radius: 6px;
  font-size: .8125rem;
  line-height: 1.45;
}}
.sr-operator-warning strong {{ color: var(--sr-ink); }}
.command-topbar .command-top-link,
.command-topbar.compact .command-top-link {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  white-space: normal;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-strip.compact {{
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 16px;
  padding: 12px;
  color: var(--sr-text);
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-radius: 8px;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-strip > span,
.stApp:has(.sr-operator-route-shell) .profile-trust-primary {{
  display: grid;
  align-content: start;
  gap: 4px;
  min-width: 0;
  padding: 0 8px;
  border-left: 1px solid var(--sr-border);
  font-size: .8125rem;
  line-height: 1.4;
  overflow-wrap: anywhere;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-primary {{
  padding-left: 0;
  border-left: 0;
}}
.stApp:has(.sr-operator-route-shell) .profile-trust-strip small,
.stApp:has(.sr-operator-route-shell) .profile-trust-label {{
  color: var(--sr-muted);
  font-size: .6875rem;
  font-weight: 700;
  line-height: 1.25;
  text-transform: uppercase;
}}
.sr-answer-panel {{
  display: grid;
  gap: 12px;
  max-width: 65rem;
  margin: 0 0 16px;
  padding: 24px;
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-left: 4px solid var(--sr-forest);
  border-radius: 12px;
}}
.sr-answer-question {{ margin: 0; color: var(--sr-muted); font-size: .8125rem; font-weight: 700; }}
.sr-answer-panel h2 {{ margin: 0; max-width: 50ch; color: var(--sr-ink); font-size: 1.25rem; line-height: 1.35; }}
.sr-answer-reason {{ margin: 0; max-width: 65ch; color: var(--sr-text); font-size: .9375rem; line-height: 1.5; }}
.research-discover-intro {{
  display: grid;
  gap: 6px;
  margin: 0 0 4px;
  padding: 10px 14px;
  background: #F4F8F5;
  border: 1px solid var(--sr-border);
  border-left: 3px solid var(--sr-forest);
  border-radius: 10px;
}}
.research-discover-intro .sr-answer-panel {{
  display: grid;
  gap: 2px;
  max-width: none;
  margin: 0;
  padding: 0;
  background: transparent;
  border: 0;
}}
.research-discover-intro .sr-answer-question {{
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}}
.research-discover-intro .sr-answer-panel h2 {{
  max-width: none;
  font-size: 1rem;
  line-height: 1.35;
}}
.research-discover-intro .sr-answer-reason {{
  max-width: none;
  font-size: .8125rem;
  line-height: 1.35;
}}
.research-discover-intro .sr-stop-rule {{
  display: flex;
  flex-wrap: wrap;
  gap: 2px 8px;
  margin: 0;
  padding: 6px 0 0;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--sr-border);
  border-left: 0;
  border-radius: 0;
  font-size: .8125rem;
  line-height: 1.35;
}}
.research-discover-intro .sr-stop-rule strong {{ white-space: nowrap; }}
.sr-primary-action, .public-primary-action {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-width: 44px;
  min-height: 44px;
  padding: 8px 16px;
  color: #FFFFFF !important;
  background: var(--sr-forest);
  border: 1px solid var(--sr-forest);
  border-radius: 6px;
  font-weight: 700;
  line-height: 1.35;
  text-decoration: none !important;
  white-space: normal;
}}
.discover-quick-company-links {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  align-items: stretch;
}}
.discover-quick-company-links > p {{
  grid-column: 1 / -1;
  margin: 0;
}}
.discover-quick-company-links .sr-primary-action {{
  box-sizing: border-box;
  width: 100%;
  min-width: 44px;
  text-align: center;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stTextInput"] input {{ min-height: 44px; }}
.stApp:has(.public-app-shell) [data-testid="stTextInput"] input {{ min-height: 44px; }}
.research-discover-browser-jump {{
  position: relative;
  z-index: 2;
  top: 0;
  height: 0;
  margin: 0;
  text-align: right;
}}
.research-discover-browser-jump a {{ color: var(--sr-forest) !important; font-weight: 650; }}
.sr-stop-rule {{
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 12px 16px;
  color: var(--sr-text);
  background: var(--sr-surface-muted);
  border-left: 3px solid var(--sr-amber);
  border-radius: 6px;
  font-size: .8125rem;
  line-height: 1.5;
}}
.sr-supporting-evidence {{ max-width: 65rem; margin: 0 0 16px; }}
.sr-supporting-evidence h2 {{ margin: 0 0 8px; color: var(--sr-ink); font-size: 1.125rem; }}
.sr-supporting-evidence ul {{ margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--sr-border); }}
.sr-evidence-row {{
  display: grid;
  grid-template-columns: minmax(10rem, 1fr) minmax(10rem, auto) minmax(0, 2fr);
  gap: 8px 16px;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--sr-border);
}}
.sr-evidence-row > * {{ min-width: 0; }}
.sr-evidence-lane {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; min-width: 0; }}
.sr-evidence-row p {{ margin: 0; color: var(--sr-text); overflow-wrap: anywhere; font-size: .8125rem; line-height: 1.5; }}
.sr-evidence-count {{ color: var(--sr-muted); font: .8125rem ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; }}
.research-desk-brief .sr-evidence-row {{
  grid-template-columns: minmax(12rem, .75fr) minmax(0, 2fr);
  align-items: start;
}}
.research-desk-brief .sr-evidence-lane {{ grid-row: 1 / span 2; }}
.research-desk-brief .sr-evidence-count {{
  grid-column: 2;
  overflow-wrap: anywhere;
  white-space: normal;
}}
.research-desk-brief .sr-evidence-row p {{ grid-column: 2; }}
.sr-status-chip {{
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 2px 8px;
  color: var(--sr-state-fg);
  background: var(--sr-state-bg);
  border: 1px solid var(--sr-state-border);
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 700;
  line-height: 1.35;
}}
.sr-next-step-prompt {{
  display: grid;
  gap: 4px;
  min-height: 44px;
  max-width: 65rem;
  padding: 10px 16px;
  color: var(--sr-text);
  background: var(--sr-surface);
  border-left: 4px solid var(--sr-forest);
  border-radius: 6px;
}}
.sr-next-step-prompt strong {{ color: var(--sr-ink); font-size: .8125rem; }}
.sr-next-step-prompt span {{ color: var(--sr-muted); font-size: .8125rem; line-height: 1.5; }}
.sr-supporting-intro {{ max-width: 65rem; padding-top: 4px; }}
.sr-supporting-intro h2 {{ margin: 0 0 4px; color: var(--sr-ink); font-size: 1.125rem; }}
.sr-supporting-intro p {{ margin: 0; color: var(--sr-muted); font-size: .8125rem; line-height: 1.5; }}
.sr-evidence-timeline {{ max-width: 65rem; }}
.sr-evidence-timeline h2 {{ margin: 0 0 8px; color: var(--sr-ink); font-size: 1.125rem; }}
.sr-evidence-timeline ol {{
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--sr-border);
}}
.public-proof-timeline-summary {{
  margin: 0 0 8px;
  color: var(--sr-muted);
  font-size: .8125rem;
  line-height: 1.5;
}}
.sr-timeline-record, .sr-timeline-empty {{
  display: grid;
  grid-template-columns: minmax(9rem, auto) minmax(10rem, .8fr) minmax(0, 2fr);
  gap: 8px 16px;
  align-items: start;
  padding: 12px 0;
  border-bottom: 1px solid var(--sr-border);
  content-visibility: auto;
  contain-intrinsic-size: auto 72px;
}}
.sr-timeline-record time {{ color: var(--sr-muted); font: .8125rem ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace; }}
.sr-timeline-record strong, .sr-timeline-empty strong {{ color: var(--sr-ink); font-size: .8125rem; }}
.sr-timeline-record p, .sr-timeline-empty p {{ margin: 0; color: var(--sr-text); font-size: .8125rem; line-height: 1.5; overflow-wrap: anywhere; }}
.sr-timeline-empty {{ grid-template-columns: 1fr; }}
.sr-detail-disclosure {{ max-width: 65rem; border-top: 1px solid var(--sr-border); }}
.sr-detail-disclosure summary {{ min-height: 44px; padding: 12px 0; color: var(--sr-ink); font-weight: 700; cursor: pointer; }}
.sr-detail-disclosure-body {{ display: grid; gap: 12px; padding: 0 0 16px; }}
.sr-detail-item {{ display: grid; gap: 4px; }}
.sr-detail-item strong {{ color: var(--sr-ink); font-size: .8125rem; }}
.sr-detail-item p {{ margin: 0; color: var(--sr-text); font-size: .8125rem; line-height: 1.5; }}
.sr-advanced-detail-marker {{
  height: 1px;
  overflow: hidden;
  color: transparent;
}}
.research-workflow-navigation {{
  position: fixed !important;
  z-index: 20;
  top: 16px;
  left: 16px;
  display: grid !important;
  align-content: start;
  gap: 8px !important;
  width: clamp(12.5rem, 16vw, 14.5rem) !important;
  max-height: calc(100vh - 32px);
  padding: 16px !important;
  overflow-y: auto;
  background: var(--sr-nav) !important;
  border: 1px solid var(--sr-nav) !important;
  border-radius: 10px !important;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stSidebar"] {{
  display: none !important;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stMain"] {{
  margin-left: 0 !important;
}}
.stApp:has(.research-workflow-navigation) [data-testid="stMainBlockContainer"] {{
  padding-left: calc(clamp(12.5rem, 16vw, 14.5rem) + 40px) !important;
}}
.research-workflow-routes {{ display: grid; gap: 4px; }}
.research-workspace-brand {{
  display: grid;
  align-content: center;
  min-height: 44px;
  color: var(--sr-nav-text) !important;
  text-decoration: none !important;
}}
.research-workspace-brand span {{ color: var(--sr-nav-muted); font-size: .75rem; }}
.research-workspace-brand strong {{ color: var(--sr-nav-text); font-size: .8125rem; line-height: 1.35; }}
.research-workflow-navigation .research-workflow-link, .research-workflow-disabled {{
  display: flex;
  align-items: center;
  min-width: 44px;
  min-height: 44px;
  padding: 8px 12px;
  color: var(--sr-nav-text) !important;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: .8125rem;
  font-weight: 650;
  line-height: 1.35;
  text-decoration: none !important;
  white-space: normal;
}}
.research-workflow-navigation .research-workflow-link[aria-current="page"] {{
  background: rgba(248, 250, 252, .12) !important;
  border-color: var(--sr-nav-text) !important;
  color: var(--sr-nav-text) !important;
}}
.research-workflow-navigation .research-workflow-evidence-current {{
  background: rgba(248, 250, 252, .12);
  border-color: var(--sr-nav-muted);
}}
.research-workflow-navigation .research-workflow-evidence-current > span {{
  color: var(--sr-nav-muted) !important;
}}
.research-workflow-navigation .research-workflow-evidence-current > strong {{
  color: var(--sr-nav-text) !important;
}}
.research-workflow-disabled {{ position: relative; color: var(--sr-nav-muted) !important; opacity: .82; cursor: not-allowed; }}
.research-workspace-mode {{
  display: grid;
  gap: 4px;
  padding-top: 12px;
  border-top: 1px solid rgba(248, 250, 252, .24);
}}
.research-workspace-mode > span {{ color: var(--sr-nav-muted); font-size: .75rem; }}
.research-workspace-mode a {{
  display: flex;
  align-items: center;
  min-width: 44px;
  min-height: 44px;
  color: var(--sr-nav-text) !important;
  font-size: .8125rem;
}}
.stApp:has(.st-key-company-workbench-document) .st-key-company-workbench-document [data-testid="stHorizontalBlock"] {{
  align-items: start;
}}
.stApp:has(.st-key-company-workbench-document) .st-key-company-workbench-document [data-testid="stColumn"]:last-child {{
  position: sticky;
  top: 1rem;
  align-self: start;
  min-height: 8rem;
  padding: 18px;
  color: var(--sr-nav-text);
  background: var(--sr-nav);
  border: 1px solid rgba(248, 250, 252, .12);
  border-radius: 18px;
  box-shadow: 0 14px 30px rgba(11, 27, 43, .12);
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-status {{
  display: grid;
  gap: 14px;
  color: var(--sr-nav-text);
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading {{
  display: grid;
  gap: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(248, 250, 252, .24);
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading h2 {{
  margin: 0;
  color: var(--sr-nav-text) !important;
  font-size: 1.125rem;
  line-height: 1.25;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading h2 * {{
  color: var(--sr-nav-text) !important;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading > span {{
  color: var(--sr-nav-muted) !important;
  font-size: .8125rem;
  line-height: 1.35;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lanes {{
  display: grid;
  gap: 8px;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane {{
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 6px;
  align-items: start;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(248, 250, 252, .24);
  border-radius: 10px;
  background: rgba(248, 250, 252, .06);
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane span {{
  color: var(--sr-nav-muted) !important;
  font-size: .875rem;
  line-height: 1.35;
  white-space: nowrap;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane strong {{
  color: var(--sr-nav-text) !important;
  font-size: .75rem;
  line-height: 1.25;
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  justify-self: start;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(248, 250, 252, .14);
  text-align: right;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane[data-evidence-state='reviewable'] strong {{
  color: #DBF5EA !important;
  background: #1E5A4B;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane[data-evidence-state='withheld'] strong {{
  color: #FFE7BA !important;
  background: #62481F;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane[data-evidence-state='unavailable'] strong {{
  color: #E2E8F0 !important;
  background: #354358;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-brief {{
  margin-top: 0;
  padding: 22px 24px;
  color: var(--sr-text);
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-radius: 20px;
  box-shadow: 0 12px 32px rgba(11, 27, 43, .07);
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-heading {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--sr-border);
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-heading h2 {{
  color: var(--sr-ink) !important;
  font-family: Inter, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
  font-size: clamp(1.5rem, 2.4vw, 2rem);
  font-weight: 700;
  letter-spacing: -.03em;
  line-height: 1.15;
  margin: 0;
  text-transform: none;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-heading h2 > span:first-child {{
  color: inherit !important;
  font: inherit;
  letter-spacing: inherit;
  text-transform: none;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-brief-mode {{
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 4px 10px;
  color: var(--sr-forest);
  background: #E6F1EB;
  border: 1px solid #C5DED0;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
  white-space: nowrap;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-priority-action {{
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer {{
  display: grid;
  align-content: start;
  min-width: 0;
  padding: 16px 18px;
  background: var(--sr-surface);
  border: 1px solid var(--sr-border);
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(11, 27, 43, .035);
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.use-now {{
  background: #EFF8F4;
  border-color: #C9E3D7;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.withheld {{
  background: #FFF8EC;
  border-color: #EEDDBA;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer[data-workbench-priority='secondary'] {{
  padding: 16px 18px;
  background: #F6F8F7;
  border-color: #E1E8E3;
  box-shadow: none;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer > span {{
  display: inline-flex;
  align-items: center;
  justify-self: start;
  min-height: 24px;
  padding: 4px 9px;
  color: var(--sr-forest);
  background: #E6F1EB;
  border-radius: 999px;
  font-size: .6875rem;
  font-weight: 800;
  letter-spacing: .035em;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.withheld > span {{
  color: #854D0E;
  background: #FBE9C4;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.changed > span {{
  color: #315D8A;
  background: #E6EEF6;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer p {{
  margin: 10px 0 0;
  color: var(--sr-text);
  font-size: 1rem;
  line-height: 1.5;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer strong {{
  margin: 10px 0 0;
  color: var(--sr-ink);
  font-size: 1rem;
  line-height: 1.45;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer small {{
  display: inline-flex;
  align-items: center;
  justify-self: start;
  margin: 10px 0 0;
  padding: 4px 8px;
  color: #475569;
  background: #E8EEEA;
  border-radius: 999px;
  font-size: .75rem;
  line-height: 1.25;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-priority-action .public-primary-action {{
  justify-self: start;
  justify-content: center;
  margin-top: 0;
  padding: 8px 14px;
  min-height: 44px;
  border-radius: 9px;
  font-size: .875rem;
  font-weight: 700;
}}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-stop {{
  margin: 0;
  padding: 10px 12px;
  color: #3F5A4B;
  background: #F1F6F2;
  border: 0;
  border-left: 3px solid var(--sr-forest);
  border-radius: 9px;
  font-size: .8125rem;
  line-height: 1.45;
}}
.stApp:has(.st-key-company-workbench-document) [data-testid="stBaseButton-primary"] {{
  min-height: 44px;
  color: var(--sr-nav-text) !important;
  background: var(--sr-forest) !important;
  border-color: var(--sr-forest) !important;
}}
.stApp:has(.st-key-company-workbench-document) [data-testid="stBaseButton-primary"] * {{
  color: var(--sr-nav-text) !important;
}}
@media (max-width: 1099px) {{
  .stApp:has(.st-key-company-workbench-document) .st-key-company-workbench-document [data-testid="stHorizontalBlock"] {{
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
  }}
  .stApp:has(.st-key-company-workbench-document) .st-key-company-workbench-document [data-testid="stColumn"] {{
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 0 !important;
  }}
  .stApp:has(.st-key-company-workbench-document) .st-key-company-workbench-document [data-testid="stColumn"]:last-child {{
    position: static;
    min-height: 44px;
    margin-top: 12px;
  }}
}}
.public-app-shell, .research-workspace-header, .research-desk-brief {{ box-shadow: none !important; }}
.research-workspace-header {{
  margin-bottom: 16px !important;
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
}}
.research-desk-brief[aria-label="Today's Research Brief"] {{
  margin: 0 0 16px !important;
  padding: 0 !important;
  background: transparent !important;
  border: 0 !important;
}}
.public-app-nav a {{ min-width: 44px; min-height: 44px; white-space: normal; }}
.public-app-shell .public-workspace-mode {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  color: var(--sr-muted);
  font-size: .8125rem;
}}
.public-app-shell .public-workspace-mode a {{ color: var(--sr-forest) !important; min-height: 44px; display: inline-flex; align-items: center; }}
.public-skip-link:focus-visible, a:focus-visible, button:focus-visible,
input:focus-visible, select:focus-visible, textarea:focus-visible, summary:focus-visible,
[role="button"]:focus-visible, [data-sr-region]:focus-visible,
.sr-evidence-timeline ol:focus-visible {{
  outline: 3px solid var(--sr-focus) !important;
  outline-offset: 3px !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"],
  .stApp:has(.research-workflow-navigation) [data-testid="stMainBlockContainer"] {{
    width: 100% !important;
    max-width: 100% !important;
    padding: 8px 12px 32px !important;
  }}
  .research-workflow-navigation {{
    position: static !important;
    display: grid !important;
    align-items: stretch;
    gap: 2px !important;
    width: 100% !important;
    max-width: 100% !important;
    min-height: 44px;
    padding: 4px !important;
    overflow: visible;
    border-radius: 10px;
  }}
  .research-workspace-brand {{ width: 100%; }}
  .research-workflow-routes {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(5rem, 1fr));
    gap: 4px;
    width: 100%;
  }}
  .research-workflow-routes .research-workflow-evidence-current {{
    grid-column: 1 / -1;
    justify-content: center;
    min-width: 0;
    text-align: center;
  }}
  .research-workspace-mode {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 8px; padding: 8px 0 0; border-top: 1px solid rgba(248, 250, 252, .24); }}
  .research-workspace-mode > span {{ grid-column: 1 / -1; align-self: center; padding: 0 4px; }}
  .research-workflow-navigation .research-workflow-link, .research-workflow-disabled {{ justify-content: center; min-width: 0; max-width: none; padding: 6px; text-align: center; }}
  .research-workspace-mode a {{ justify-content: center; min-width: 44px; max-width: none; }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-brief {{
    padding: 12px;
    border-radius: 14px;
    box-shadow: none;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-grid {{
    grid-template-columns: 1fr;
    gap: 8px;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-priority-action {{
    grid-template-columns: 1fr;
    gap: 8px;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer {{
    padding: 10px 12px;
    border-radius: 10px;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer[data-workbench-priority='secondary'] {{
    padding: 10px 12px;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer p,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer strong,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer small {{
    margin-top: 5px !important;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer p {{
    font-size: .875rem;
    line-height: 1.4;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-priority-action .public-primary-action {{
    margin-top: 0 !important;
    min-height: 44px;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-heading {{
    margin-bottom: 10px !important;
    padding-bottom: 10px;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-stop {{
    margin-top: 8px;
    padding: 8px 10px;
  }}
  .sr-context-bar {{ gap: 8px 16px; }}
  .sr-context-item {{ min-width: min(9rem, 100%); }}
  .sr-page-title h1 {{ font-size: 1.375rem; }}
  .sr-operator-route-shell {{ gap: 10px; padding: 16px; }}
  .sr-operator-route-title h1 {{ font-size: 1.25rem; }}
  .sr-operator-warning {{ grid-template-columns: 1fr; gap: 4px; }}
  .stApp:has(.sr-operator-route-shell) .profile-trust-strip.compact {{
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px 0;
    padding: 10px;
  }}
  .stApp:has(.sr-operator-route-shell) .profile-trust-strip > :nth-child(odd) {{
    padding-left: 0;
    border-left: 0;
  }}
  .sr-answer-panel {{ gap: 12px; padding: 16px; }}
  .sr-answer-panel h2 {{ font-size: 1.0625rem; }}
  .discover-quick-company-links {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
  .sr-primary-action, .public-primary-action {{ width: 100%; }}
  .sr-evidence-row, .sr-timeline-record {{ grid-template-columns: 1fr; }}
  .research-desk-brief .sr-evidence-row {{ grid-template-columns: 1fr; }}
  .research-desk-brief .sr-evidence-lane,
  .research-desk-brief .sr-evidence-count,
  .research-desk-brief .sr-evidence-row p {{
    grid-column: 1;
    grid-row: auto;
  }}
}}
@media (min-width: 375px) and (max-width: 640px) {{
  .research-workflow-navigation {{
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 4px 8px !important;
    padding: 6px !important;
  }}
  .research-workspace-brand {{
    grid-column: 1;
    grid-row: 1;
    width: auto;
    min-width: 0;
  }}
  .research-workspace-brand span {{ display: none; }}
  .research-workspace-brand strong {{ font-size: .75rem; line-height: 1.2; }}
  .research-workflow-routes {{
    grid-column: 1 / -1;
    grid-row: 2;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 2px;
  }}
  .research-workflow-navigation .research-workflow-link,
  .research-workflow-navigation .research-workflow-disabled {{
    min-height: 44px;
    padding: 4px;
    font-size: .75rem;
    line-height: 1.2;
  }}
  .research-workspace-mode {{
    grid-column: 2;
    grid-row: 1;
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 0;
    border-top: 0;
  }}
  .research-workspace-mode > span {{ display: none; }}
  .research-workspace-mode a {{
    min-width: 44px;
    min-height: 44px;
    padding: 4px;
    font-size: .75rem;
  }}
  .research-workspace-header .sr-context-bar {{
    display: grid;
    grid-template-columns: minmax(0, .65fr) minmax(0, 1.5fr) minmax(0, .9fr);
    gap: 4px 8px;
    margin: 0 0 6px;
    padding: 6px 0 8px;
  }}
  .research-workspace-header .sr-context-item {{
    min-width: 0;
    gap: 2px;
  }}
  .research-workspace-header .sr-context-item dt {{
    font-size: .625rem;
    line-height: 1.2;
  }}
  .research-workspace-header .sr-context-item dd {{
    font-size: .75rem;
    line-height: 1.3;
  }}
  .research-workspace-header .sr-page-title {{ margin: 0 0 8px; }}
  .research-workspace-header .sr-page-title h1 {{ font-size: 1.25rem; }}
  .research-workspace-header .sr-page-title p {{
    margin: 3px 0 0;
    font-size: .875rem;
    line-height: 1.3;
  }}
  .research-discover-result .selector-result-row {{
    grid-template-columns: minmax(0, 1fr) auto !important;
    grid-template-areas: 'identity action' 'answers answers';
    gap: 8px;
    align-items: center;
    padding: 10px 12px;
  }}
  .research-discover-result .selector-result-identity {{ grid-area: identity; }}
  .research-discover-result .selector-actions {{ grid-area: action; justify-self: end; }}
  .research-discover-result .research-discover-answers {{ grid-area: answers; }}
  .research-discover-result .selector-action-link {{ width: auto !important; }}
}}
@media (max-width: 360px) {{
  .research-discover-browser-jump {{
    position: static;
    height: auto;
    margin: 0 0 4px;
    text-align: left;
  }}
}}
@media (forced-colors: active) {{
  .public-app-nav a[aria-current="page"],
  .research-workflow-link[aria-current="page"],
  [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
  .sr-status-chip,
  .sr-stop-rule {{
    border: 2px solid CanvasText;
    outline: 1px solid CanvasText;
    outline-offset: -4px;
  }}
  .public-skip-link:focus-visible, a:focus-visible, button:focus-visible {{
    outline: 3px solid Highlight !important;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-status,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading h2,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading h2 *,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading > span,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane span,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane strong {{
    color: CanvasText !important;
  }}
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane {{
    border-color: CanvasText !important;
  }}
  .stApp:has(.st-key-company-workbench-document) [data-testid="stBaseButton-primary"] {{
    color: ButtonText !important;
    background: ButtonFace !important;
    border-color: ButtonText !important;
  }}
  .stApp:has(.st-key-company-workbench-document) [data-testid="stBaseButton-primary"] * {{
    color: ButtonText !important;
  }}
}}
@media (prefers-reduced-motion: reduce) {{
  .stApp, .stApp *, .stApp *::before, .stApp *::after {{
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    transition-delay: 0ms !important;
    scroll-behavior: auto !important;
  }}
}}
""".strip() + "\n" + research_dossier_css()


def research_dossier_css() -> str:
    """Scoped, information-first presentation for Personal Research routes."""

    return """
.stApp:has(.research-workflow-navigation) [data-testid="stMainBlockContainer"] {
  max-width: 90rem !important;
  padding: 0 28px 56px !important;
}
.research-workflow-navigation {
  position: sticky !important;
  top: 0 !important;
  left: auto !important;
  z-index: 30;
  display: grid !important;
  grid-template-columns: minmax(11rem, auto) minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px 24px !important;
  width: 100% !important;
  max-height: none !important;
  margin: 0 0 16px !important;
  padding: 9px 0 !important;
  overflow: visible !important;
  color: #17232f !important;
  background: #f6f7f4 !important;
  border: 0 !important;
  border-bottom: 1px solid #d7dfda !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}
.research-workspace-brand { min-height: 44px; }
.research-workspace-brand span { display: none; }
.research-workspace-brand strong {
  max-width: 12rem;
  color: #17232f !important;
  font-size: .9rem;
  font-weight: 760;
  line-height: 1.18;
}
.research-workflow-routes {
  display: flex !important;
  align-items: center;
  flex-wrap: nowrap !important;
  gap: 3px !important;
  min-width: 0;
}
.research-workflow-navigation .research-workflow-link,
.research-workflow-navigation .research-workflow-disabled {
  display: inline-flex;
  flex: 0 0 auto;
  min-height: 44px;
  padding: 9px 12px;
  color: #41505e !important;
  border-radius: 8px;
  font-size: .85rem;
  font-weight: 620;
}
.research-workflow-navigation .research-workflow-link[aria-current="page"] {
  color: #0f5e4e !important;
  background: #e4f0e9 !important;
  border-color: transparent !important;
}
.research-workflow-navigation .research-workflow-disabled { color: #7b878f !important; }
.research-workspace-mode {
  position: relative;
  display: block !important;
  padding: 0 !important;
  border: 0 !important;
}
.research-workspace-mode summary {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 8px 10px;
  color: #52615c;
  cursor: pointer;
  font-size: .78rem;
  font-weight: 650;
  white-space: nowrap;
}
.research-workspace-mode > div {
  position: absolute;
  right: 0;
  min-width: 11rem;
  padding: 6px;
  background: #fff;
  border: 1px solid #d7dfda;
  border-radius: 10px;
  box-shadow: 0 12px 26px rgba(15, 23, 42, .1);
}
.research-workspace-mode a {
  min-height: 44px;
  padding: 9px 11px;
  color: #243244 !important;
  text-decoration: none !important;
}
.research-workspace-header { margin-bottom: 10px !important; }
.research-workspace-header .sr-context-bar {
  display: flex;
  align-items: baseline;
  gap: 4px 18px;
  margin-bottom: 5px !important;
  padding: 4px 0 7px !important;
}
.research-workspace-header .sr-context-item {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  min-width: 0;
}
.research-workspace-header .sr-context-item dt,
.research-workspace-header .sr-context-item dd { font-size: .72rem; }
.research-workspace-header .sr-page-title { margin-bottom: 5px !important; }
.research-workspace-header .sr-page-title h1 { font-size: clamp(1.45rem, 2vw, 1.85rem) !important; }
.research-discover-scope {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 2px 0 8px;
  padding: 8px 0;
  color: #475569;
  border-bottom: 1px solid #dce4df;
  font-size: .78rem;
}
.research-discover-scope-counts { display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: center; }
.research-discover-scope-counts strong { color: #17232f; font-size: .85rem; }
.research-discover-scope p { margin: 0; }
.research-discover-scope .sr-stop-rule {
  display: block;
  padding: 2px 8px;
  border-left-width: 2px;
  border-radius: 3px;
  font-size: .76rem;
  line-height: 1.4;
}
.research-discover-scope-detail { margin-left: auto; }
.research-discover-scope-detail summary { min-height: 44px; display: flex; align-items: center; cursor: pointer; }
.research-discover-scope-detail p { max-width: 60ch; padding: 2px 0 8px; }
.research-discover-result {
  margin-top: 4px !important;
  border: 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}
.research-discover-result .selector-result-row {
  display: grid;
  grid-template-columns: minmax(8rem, .7fr) minmax(0, 2fr) auto;
  gap: 8px 20px;
  align-items: center;
  min-height: 66px;
  margin: 0;
  padding: 10px 12px;
  background: #fff;
  border: 0;
  border-bottom: 1px solid #e0e6e2;
  border-radius: 0;
  box-shadow: none;
}
.research-discover-result .selector-result-row:first-child { border-top: 1px solid #e0e6e2; }
.research-discover-result .selector-result-ticker { font-size: 1rem; font-weight: 760; }
.research-discover-result .selector-action-link { min-height: 44px; padding: 9px 12px; }
.research-discover-result .research-discover-answers {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px 12px;
}
.research-discover-result .research-discover-answer {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 2px 5px;
}
.research-discover-result .research-discover-answer-label {
  display: inline;
  margin: 0;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: none;
}
.research-discover-result .research-discover-answer-value {
  font-size: .78rem;
  line-height: 1.35;
}
.research-discover-result .research-discover-details {
  flex-basis: 100%;
  margin-top: 0;
}
.research-discover-result .research-discover-details summary {
  min-height: 44px;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-brief {
  margin: 0;
  padding: 4px 0 12px;
  background: transparent;
  border: 0;
  border-bottom: 1px solid #dce4df;
  border-radius: 0;
  box-shadow: none;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-heading {
  margin-bottom: 4px;
  padding-bottom: 8px;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 22px;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer,
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.use-now,
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.withheld,
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer[data-workbench-priority="secondary"] {
  padding: 8px 0;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer > span {
  padding: 0;
  color: #64748b;
  background: transparent;
  border-radius: 0;
  font-size: .69rem;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer p,
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer strong { margin: 4px 0 0; font-size: .88rem; line-height: 1.4; }
.stApp:has(.st-key-company-workbench-document) .company-workbench-priority-action { gap: 8px 16px; padding-top: 5px; }
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.next-task {
  grid-column: 1 / -1;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 12px;
  padding: 5px 0;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer.next-task strong {
  margin: 0;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-follow-up {
  grid-column: 1 / -1;
  margin-top: 2px;
  border-top: 1px solid #e0e6e2;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-follow-up summary {
  display: flex;
  align-items: center;
  min-height: 44px;
  color: #52615c;
  cursor: pointer;
  font-size: .78rem;
  font-weight: 700;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-follow-up-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 22px;
  padding-bottom: 8px;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-primary-stop {
  background: transparent;
  border: 0;
  border-left: 2px solid #aebbb3;
  border-radius: 0;
  padding: 6px 10px;
  color: #52615c;
  font-size: .75rem;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-status {
  display: block;
  margin: 8px 0 16px;
  padding: 0;
  color: #243244;
  background: transparent;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 20px;
  padding: 0 0 8px;
  border-bottom: 1px solid #dce4df;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading h2 { color: #17232f !important; font-size: 1.05rem; }
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading h2 > span:first-child {
  color: inherit !important;
  font: inherit;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-heading > span { color: #52615c !important; }
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table {
  display: table;
  width: 100%;
  border-collapse: collapse;
  color: #243244;
  background: transparent;
  font-size: .8rem;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table thead { background: #edf2ee; }
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table th,
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table td {
  padding: 9px 10px;
  border-bottom: 1px solid #e0e6e2;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table th { color: #52615c; font-weight: 700; }
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table td small {
  display: block;
  line-height: 1.4;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table td small + small {
  margin-top: 3px;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane {
  display: table-row;
  background: transparent;
  border: 0;
  border-radius: 0;
}
.stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane strong {
  color: #243244 !important;
  background: transparent;
  border: 0;
  border-radius: 0;
  padding: 0;
}
.st-key-company-sec-annual-check {
  margin: 4px 0 14px;
  padding: 10px 0 14px;
  border: 0;
  border-bottom: 1px solid #dce4df;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.company-sec-annual-preview .sec-annual-table-scroll {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid #dce4df;
  border-radius: 8px;
  background: #fff;
}
.company-sec-annual-preview .sec-annual-field-table {
  width: 100%;
  min-width: 38rem;
  border-collapse: collapse;
  color: #243244;
  font-size: .81rem;
  line-height: 1.4;
}
.company-sec-annual-preview .sec-annual-field-table caption {
  padding: 10px 12px;
  color: #243244;
  font-weight: 720;
  text-align: left;
}
.company-sec-annual-preview .sec-annual-field-table th,
.company-sec-annual-preview .sec-annual-field-table td {
  padding: 9px 12px;
  border-top: 1px solid #e0e6e2;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}
.company-sec-annual-preview .sec-annual-field-table thead th {
  color: #52615c;
  background: #edf2ee;
  font-size: .72rem;
  font-weight: 750;
}
.company-sec-annual-preview .sec-annual-field-row.is-withheld { background: #fdfbf6; }
.company-sec-annual-preview .sec-annual-field-name { display: block; color: #17232f; font-weight: 720; }
.company-sec-annual-preview .sec-annual-field-row code {
  display: block;
  width: fit-content;
  margin-top: 2px;
  padding: 0;
  color: #64748b !important;
  background: transparent !important;
  font-size: .68rem;
}
.company-sec-annual-preview .sec-annual-field-value {
  color: #0f5e4e;
  font-weight: 740;
  font-variant-numeric: tabular-nums;
}
.company-sec-annual-preview .sec-annual-field-reason { color: #79551c; }
.research-discover-result .research-discover-details {
  margin-top: 0;
  color: #52615c;
  font-size: .76rem;
}
.research-discover-result .research-discover-details summary {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  cursor: pointer;
  font-weight: 650;
}
.research-discover-result .research-discover-details[open] {
  grid-column: 1 / -1;
  padding: 5px 0;
}
.research-discover-result .research-discover-saved-context { color: #64748b; font-size: .72rem; }
@media (max-width: 900px) and (min-width: 641px) {
  .research-workflow-navigation {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0 8px !important;
  }
  .research-workspace-brand { grid-column: 1; grid-row: 1; }
  .research-workflow-routes {
    grid-column: 1 / -1;
    grid-row: 2;
    display: grid !important;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px !important;
  }
  .research-workflow-navigation .research-workflow-link,
  .research-workflow-navigation .research-workflow-disabled {
    justify-content: center;
    min-width: 0;
    text-align: center;
    white-space: normal;
  }
  .research-workspace-mode { grid-column: 2; grid-row: 1; }
}
@media (max-width: 640px) {
  .stApp:has(.research-workflow-navigation) [data-testid="stMainBlockContainer"] { padding: 0 12px 40px !important; }
  .research-workflow-navigation {
    position: sticky !important;
    top: 0 !important;
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0 8px !important;
    margin-bottom: 8px !important;
    padding: 4px 0 !important;
    border-radius: 0 !important;
  }
  .research-workspace-brand { grid-column: 1; min-width: 0; }
  .research-workspace-brand strong { max-width: none; font-size: .78rem; }
  .research-workflow-routes {
    grid-column: 1 / -1;
    grid-row: 2;
    display: grid !important;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 3px !important;
    overflow: visible;
  }
  .research-workflow-navigation .research-workflow-link,
  .research-workflow-navigation .research-workflow-disabled {
    justify-content: center;
    min-width: 0;
    padding: 7px 3px;
    font-size: .7rem;
    text-align: center;
    white-space: normal;
  }
  .research-workspace-mode { grid-column: 2; grid-row: 1; }
  .research-workspace-mode summary { min-height: 44px; font-size: .7rem; }
  .research-discover-scope { align-items: start; gap: 2px 8px; margin-bottom: 4px; padding: 3px 0; }
  .research-discover-scope-counts { gap: 2px 9px; }
  .research-discover-scope-detail { margin-left: 0; }
  .research-discover-result .selector-result-row {
    grid-template-columns: minmax(0, 1fr) auto !important;
    grid-template-areas: 'identity action' 'answers answers';
    gap: 3px 8px;
    min-height: 54px;
    padding: 8px 4px;
  }
  .research-discover-result .selector-result-identity { grid-area: identity; }
  .research-discover-result .selector-actions { grid-area: action; justify-self: end; }
  .research-discover-result .research-discover-answers {
    grid-area: answers;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas: 'status detail' 'summary summary';
    align-items: center;
    gap: 0 6px;
  }
  .research-discover-result .research-discover-answer:first-child { grid-area: status; }
  .research-discover-result .research-discover-answer:nth-child(2) { grid-area: summary; }
  .research-discover-result .research-discover-details { grid-area: detail; }
  .research-discover-result .selector-action-link { padding: 8px; font-size: .75rem; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-brief { padding: 2px 0 8px; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-grid { grid-template-columns: 1fr; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-follow-up-grid { grid-template-columns: 1fr; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-primary-answer[data-workbench-priority="secondary"] { padding: 5px 0; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-priority-action { grid-template-columns: 1fr; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table tbody,
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane { display: block; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table thead {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-lane { padding: 4px 0; border-bottom: 1px solid #dce4df; }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table td {
    display: grid;
    grid-template-columns: minmax(5.5rem, .45fr) minmax(0, 1fr);
    gap: 8px;
    padding: 3px 2px;
    border: 0;
  }
  .stApp:has(.st-key-company-workbench-document) .company-workbench-evidence-table td::before {
    content: attr(data-label);
    color: #64748b;
    font-size: .72rem;
    font-weight: 700;
  }
}
@media (max-width: 300px) {
  .research-workflow-routes {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .research-discover-result .research-discover-answers {
    display: flex;
  }
  .research-discover-result .research-discover-details { flex-basis: 100%; }
}
""".strip()


def legacy_research_accessibility_css() -> str:
    """Return the frozen Research-only media preference fallback CSS."""

    return """
@media (forced-colors: active) {
  .stApp a:focus-visible,
  .stApp button:focus-visible,
  .stApp input:focus-visible,
  .stApp select:focus-visible,
  .stApp textarea:focus-visible,
  .stApp [role="button"]:focus-visible,
  .stApp [role="radio"]:focus-visible,
  .stApp [role="tab"]:focus-visible,
  .stApp summary:focus-visible,
  .stApp [tabindex]:not([tabindex="-1"]):focus-visible {
    outline: 3px solid Highlight !important;
    outline-offset: 3px !important;
    box-shadow: none !important;
  }
  .research-workflow-link[aria-current='page'] {
    border: 2px solid Highlight !important;
    outline: 1px solid CanvasText !important;
    outline-offset: -4px !important;
  }
  .research-workspace-boundary,
  .observation-recency-summary,
  .research-state-message,
  .signal-card {
    border-color: CanvasText !important;
  }
  .research-workspace-boundary {
    border-style: solid !important;
    border-width: 1px !important;
    border-radius: 4px;
    padding: 0.2rem 0.35rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .stApp,
  .stApp *,
  .stApp *::before,
  .stApp *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    transition-delay: 0ms !important;
    scroll-behavior: auto !important;
  }
}
""".strip()


def render_stylesheet(css: str) -> str:
    """Wrap already-composed CSS in the exact stylesheet DOM envelope."""

    return f"<style>{css}</style>"


def escape_text(value: object) -> str:
    """Escape a value at an HTML text boundary."""

    return html.escape(str(value), quote=False)


def escape_attribute(value: object) -> str:
    """Escape a value at a quoted HTML attribute boundary."""

    return html.escape(str(value), quote=True)
