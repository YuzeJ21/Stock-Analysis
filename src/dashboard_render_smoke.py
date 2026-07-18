from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from streamlit.testing.v1 import AppTest

from src.paths import resolve_project_root


@dataclass(frozen=True)
class DashboardRenderRoute:
    name: str
    query_params: tuple[tuple[str, str], ...]
    required_markers: tuple[str, ...]


@dataclass(frozen=True)
class DashboardRenderResult:
    name: str
    exceptions: tuple[str, ...]
    missing_markers: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.exceptions and not self.missing_markers


PUBLIC_RENDER_ROUTES: tuple[DashboardRenderRoute, ...] = (
    DashboardRenderRoute(
        name="Home",
        query_params=(("mode", "public"),),
        required_markers=("What is this product and where do I start?", "Research-only", "No data, no conclusion", "Start with Stock Selector"),
    ),
    DashboardRenderRoute(
        name="Stock Selector",
        query_params=(("mode", "public"), ("page", "stock-selector")),
        required_markers=("Stock Selector", "Which stock can I review?", "Research-only"),
    ),
    DashboardRenderRoute(
        name="Single-Stock Report",
        query_params=(
            ("mode", "public"),
            ("page", "single-stock-report"),
            ("ticker", "NVDA"),
            ("open", "1"),
        ),
        required_markers=("What can I use for this ticker right now?", "NVDA", "Open Data Health"),
    ),
    DashboardRenderRoute(
        name="Data Health",
        query_params=(("mode", "public"), ("page", "data-health")),
        required_markers=("Price / setup", "Fundamentals / DCF", "Peers", "Optional inputs"),
    ),
    DashboardRenderRoute(
        name="Proof History",
        query_params=(("mode", "public"), ("page", "proof-history")),
        required_markers=("Latest evidence",),
    ),
)


RESEARCH_RENDER_ROUTES: tuple[DashboardRenderRoute, ...] = (
    DashboardRenderRoute(
        name="Research Desk",
        query_params=(("mode", "research"),),
        required_markers=("Research Desk", "Focused cohort", "Weekly research summary", "What changed?", "What should I review next?", "Research-only"),
    ),
    DashboardRenderRoute(
        name="Discover",
        query_params=(("mode", "research"), ("page", "discover")),
        required_markers=("Discover", "Focused cohort", "Which stock can I review?", "Research-only"),
    ),
    DashboardRenderRoute(
        name="Company Workbench",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "NVDA"),
            ("open", "1"),
        ),
        required_markers=(
            "Company Workbench",
            "Selected Company",
            "What Changed",
            "Business Trend",
            "Valuation",
            "Forward View",
            "What Remains Withheld",
            "Research Conclusion",
            "Next Research Task",
            "Advanced Evidence",
            "Research-only",
        ),
    ),
    DashboardRenderRoute(
        name="Monitor",
        query_params=(("mode", "research"), ("page", "monitor")),
        required_markers=("Monitor", "Research change monitor", "Research-only"),
    ),
)


def _rendered_markdown(app: AppTest) -> str:
    return "\n".join(item.value for item in app.markdown)


def render_public_routes(
    base_dir: Path | str | None = None,
    *,
    routes: Iterable[DashboardRenderRoute] = PUBLIC_RENDER_ROUTES,
    timeout: int = 120,
) -> list[DashboardRenderResult]:
    root = resolve_project_root(base_dir)
    dashboard_path = root / "src" / "dashboard.py"
    results: list[DashboardRenderResult] = []

    for route in routes:
        app = AppTest.from_file(str(dashboard_path), default_timeout=timeout)
        app.query_params.update(dict(route.query_params))
        app.run(timeout=timeout)
        rendered = _rendered_markdown(app)
        exceptions = tuple(str(item.value) for item in app.exception)
        missing_markers = tuple(marker for marker in route.required_markers if marker not in rendered)
        results.append(
            DashboardRenderResult(
                name=route.name,
                exceptions=exceptions,
                missing_markers=missing_markers,
            )
        )

    return results


def render_dashboard_smoke(results: Iterable[DashboardRenderResult]) -> str:
    lines = [
        "Dashboard render smoke",
        "Read-only: renders the public route contract with Streamlit AppTest; it does not refresh data, import rows, apply changes, stage files, commit, or push.",
    ]
    for result in results:
        status = "passed" if result.passed else "failed"
        lines.append(f"- {result.name}: {status}")
        if result.exceptions:
            lines.append(f"  exceptions: {' | '.join(result.exceptions)}")
        if result.missing_markers:
            lines.append(f"  missing markers: {', '.join(result.missing_markers)}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the public Streamlit routes without starting a long-lived server.")
    parser.add_argument("--root", default=".", help="Project root containing src/dashboard.py")
    args = parser.parse_args()

    results = render_public_routes(Path(args.root))
    print(render_dashboard_smoke(results))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
