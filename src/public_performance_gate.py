from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from src.paths import resolve_project_root


@dataclass(frozen=True)
class Viewport:
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass(frozen=True)
class PublicRouteSpec:
    name: str
    route: str
    first_useful_marker: str
    full_markers: tuple[str, ...]
    critical: bool


@dataclass(frozen=True)
class PerformanceThresholds:
    shell_seconds: float = 1.0
    first_useful_seconds: float = 3.0
    warm_full_settle_seconds: float = 5.0
    cold_full_settle_seconds: float = 10.0


@dataclass(frozen=True)
class RouteTimingSample:
    route: str
    viewport: str
    run_kind: str
    shell_seconds: float | None
    first_useful_seconds: float | None
    full_settle_seconds: float | None
    success: bool
    failure: str = ""


@dataclass(frozen=True)
class PerformanceGateResult:
    verdict: str
    failures: tuple[str, ...]


DEFAULT_VIEWPORTS: tuple[Viewport, ...] = (
    Viewport(1280, 720),
    Viewport(390, 844),
)


DEFAULT_ROUTE_SPECS: tuple[PublicRouteSpec, ...] = (
    PublicRouteSpec(
        "Home",
        "/?mode=public",
        "What is this product and where do I start?",
        ("Saved readiness", "Start with Stock Selector", "Research-only"),
        False,
    ),
    PublicRouteSpec(
        "Stock Selector",
        "/?mode=public&page=stock-selector",
        "Which stock can I review?",
        ("Stock Selector", "Search this review queue", "Research-only"),
        True,
    ),
    PublicRouteSpec(
        "Single-Stock Report",
        "/?mode=public&page=single-stock-report&ticker=NVDA&open=1",
        "What can I use for this ticker right now?",
        ("SELECTED TICKER", "USE NOW", "STILL WITHHELD", "Open Data Health"),
        True,
    ),
    PublicRouteSpec(
        "Data Health",
        "/?mode=public&page=data-health",
        "What can I use and what stays unavailable?",
        ("Price / setup", "Fundamentals / DCF", "Peers", "Optional inputs"),
        True,
    ),
    PublicRouteSpec(
        "Proof History",
        "/?mode=public&page=proof-history",
        "What evidence changed a readiness state?",
        ("Latest evidence", "Advanced: proof ledger details", "Research-only"),
        False,
    ),
)


RESEARCH_ROUTE_SPECS: tuple[PublicRouteSpec, ...] = (
    PublicRouteSpec(
        "Research Desk",
        "/?mode=research&page=research-desk",
        "Weekly research summary",
        (
            "Weekly research summary",
            "What should I review next?",
            "Open Discover",
            "Advanced Evidence",
            "Research-only",
        ),
        True,
    ),
    PublicRouteSpec(
        "Discover",
        "/?mode=research&page=discover",
        "Find a Company",
        (
            "Discover",
            "Screen eligibility — when supported",
            "Browse saved companies",
            "Search saved companies",
            "Advanced: cohort readiness context",
            "Research-only",
        ),
        True,
    ),
    PublicRouteSpec(
        "Company Workbench",
        "/?mode=research&page=company-workbench&ticker=NVDA&open=1",
        "USE NOW",
        (
            "Company Workbench",
            "Advanced: selected-company lane coverage",
            "What Changed",
            "Research Decision Lab",
            "Business Trend",
            "Valuation",
            "Forward View",
            "What Remains Withheld",
            "Research Conclusion",
            "Next Research Task",
            "Research-only",
        ),
        True,
    ),
    PublicRouteSpec(
        "Monitor",
        "/?mode=research&page=monitor",
        "Follow-up Queue",
        (
            "Follow-up Queue",
            "SINCE LAST REVIEW",
            "NEEDS VERIFICATION",
            "WAITING ON EVIDENCE",
            "SCHEDULED CONTEXT",
            "EVIDENCE FRESHNESS",
            "Advanced: Monitor evidence",
            "Advanced: five-company Earnings Nowcast readiness",
            "Research-only",
        ),
        True,
    ),
)


DEFAULT_CHROME_CANDIDATES: tuple[Path, ...] = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
    Path("/usr/bin/chromium-browser"),
)


def nearest_rank_percentile(values: Iterable[float], percentile: int) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("at least one timing value is required")
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be between 1 and 100")
    rank = max(1, math.ceil((percentile / 100) * len(ordered)))
    return ordered[rank - 1]


def _timing_values(
    samples: Iterable[RouteTimingSample],
    *,
    run_kind: str | None,
    field: str,
) -> list[float]:
    values: list[float] = []
    for sample in samples:
        if not sample.success or (run_kind is not None and sample.run_kind != run_kind):
            continue
        value = getattr(sample, field)
        if value is not None:
            values.append(float(value))
    return values


def summarize_route_timings(samples: Iterable[RouteTimingSample]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[RouteTimingSample]] = {}
    for sample in samples:
        grouped.setdefault((sample.route, sample.viewport), []).append(sample)

    rows: list[dict[str, object]] = []
    for (route, viewport), group in sorted(grouped.items()):
        failures = [sample for sample in group if not sample.success]
        warm_shell = _timing_values(group, run_kind="warm", field="shell_seconds")
        cold_shell = _timing_values(group, run_kind="cold", field="shell_seconds")
        warm_first_useful = _timing_values(group, run_kind="warm", field="first_useful_seconds")
        cold_first_useful = _timing_values(group, run_kind="cold", field="first_useful_seconds")
        warm_full = _timing_values(group, run_kind="warm", field="full_settle_seconds")
        cold_full = _timing_values(group, run_kind="cold", field="full_settle_seconds")
        warm_run_count = sum(sample.success and sample.run_kind == "warm" for sample in group)
        cold_run_count = sum(sample.success and sample.run_kind == "cold" for sample in group)
        rows.append(
            {
                "route": route,
                "viewport": viewport,
                "run_count": len(group),
                "failure_count": len(failures),
                "warm_run_count": warm_run_count,
                "cold_run_count": cold_run_count,
                "success": not failures,
                "warm_shell_p90_seconds": nearest_rank_percentile(warm_shell, 90) if warm_shell else None,
                "cold_shell_max_seconds": max(cold_shell) if cold_shell else None,
                "warm_first_useful_p90_seconds": (
                    nearest_rank_percentile(warm_first_useful, 90) if warm_first_useful else None
                ),
                "cold_first_useful_max_seconds": max(cold_first_useful) if cold_first_useful else None,
                "warm_full_settle_p90_seconds": nearest_rank_percentile(warm_full, 90) if warm_full else None,
                "cold_full_settle_max_seconds": max(cold_full) if cold_full else None,
                "failures": tuple(sample.failure for sample in failures if sample.failure),
            }
        )
    return rows


def evaluate_performance_gate(
    summary: Iterable[dict[str, object]],
    *,
    critical_routes: set[str],
    thresholds: PerformanceThresholds,
    min_warm_runs: int = 0,
    min_cold_runs: int = 0,
) -> PerformanceGateResult:
    failures: list[str] = []
    for row in summary:
        route = str(row["route"])
        if route not in critical_routes:
            continue
        failure_count = int(row.get("failure_count", 0))
        if failure_count:
            failures.append(f"{route}: {failure_count} failed timing run(s)")
        warm_run_count = int(row.get("warm_run_count", 0))
        cold_run_count = int(row.get("cold_run_count", 0))
        if warm_run_count < min_warm_runs:
            failures.append(f"{route}: warm sample count {warm_run_count} is below {min_warm_runs}")
        if cold_run_count < min_cold_runs:
            failures.append(f"{route}: cold sample count {cold_run_count} is below {min_cold_runs}")
        checks = (
            ("warm_shell_p90_seconds", thresholds.shell_seconds, "warm shell p90"),
            ("cold_shell_max_seconds", thresholds.shell_seconds, "cold shell max"),
            (
                "warm_first_useful_p90_seconds",
                thresholds.first_useful_seconds,
                "warm first-useful p90",
            ),
            (
                "cold_first_useful_max_seconds",
                thresholds.first_useful_seconds,
                "cold first-useful max",
            ),
            ("warm_full_settle_p90_seconds", thresholds.warm_full_settle_seconds, "warm full-settle p90"),
            ("cold_full_settle_max_seconds", thresholds.cold_full_settle_seconds, "cold full-settle max"),
        )
        for key, limit, label in checks:
            value = row.get(key)
            if value is not None and float(value) > limit:
                failures.append(f"{route}: {label} {float(value):.3f}s exceeds {limit:.3f}s")
    return PerformanceGateResult("failed" if failures else "passed", tuple(failures))


def demo_snapshot_identity(base_dir: Path | str | None = None) -> dict[str, object]:
    root = resolve_project_root(base_dir)
    manifest_path = root / "data" / "demo" / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = payload.get("files", {})
    canonical_rows = [
        {
            "name": name,
            "sha256": str(detail.get("sha256", "")),
            "row_count": int(detail.get("row_count", 0) or 0),
        }
        for name, detail in sorted(files.items())
    ]
    canonical = json.dumps(canonical_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "manifest_path": "data/demo/manifest.json",
        "file_count": len(canonical_rows),
        "row_count": sum(row["row_count"] for row in canonical_rows),
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


def find_chrome_executable(candidates: Iterable[Path] = DEFAULT_CHROME_CANDIDATES) -> Path | None:
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def performance_result_payload(
    base_dir: Path | str | None,
    samples: Iterable[RouteTimingSample],
    *,
    commit: str,
    environment: str,
    critical_routes: set[str] | None = None,
    thresholds: PerformanceThresholds | None = None,
    workflow: str = "public",
    min_warm_runs: int = 0,
    min_cold_runs: int = 0,
) -> dict[str, object]:
    sample_rows = list(samples)
    limits = thresholds or PerformanceThresholds()
    summary = summarize_route_timings(sample_rows)
    critical = critical_routes or {route.name for route in DEFAULT_ROUTE_SPECS if route.critical}
    if sample_rows:
        gate = evaluate_performance_gate(
            summary,
            critical_routes=critical,
            thresholds=limits,
            min_warm_runs=min_warm_runs,
            min_cold_runs=min_cold_runs,
        )
    else:
        gate = PerformanceGateResult("failed", ("No browser timing samples were recorded",))
    return {
        "mode": "browser",
        "workflow": workflow,
        "verdict": gate.verdict,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": commit,
        "environment": environment,
        "demo_snapshot": demo_snapshot_identity(base_dir),
        "thresholds": asdict(limits),
        "samples": [asdict(sample) for sample in sample_rows],
        "summary": summary,
        "failures": list(gate.failures),
        "boundary": (
            "Performance evidence only. It does not refresh data, unlock blocked inputs, provide investment advice, "
            "connect to brokers, route orders, or enable auto-trading."
        ),
    }


def performance_progress_line(sample: RouteTimingSample, *, index: int, total: int) -> str:
    prefix = f"[{index}/{total}] {sample.route} {sample.viewport} {sample.run_kind}"
    if not sample.success:
        return f"{prefix}: failed; {sample.failure or 'unknown browser failure'}"
    first = f"{sample.first_useful_seconds:.3f}s" if sample.first_useful_seconds is not None else "n/a"
    full = f"{sample.full_settle_seconds:.3f}s" if sample.full_settle_seconds is not None else "n/a"
    return f"{prefix}: passed; first={first}; full={full}"


def performance_contract_payload(
    base_dir: Path | str | None = None,
    *,
    route_specs: Iterable[PublicRouteSpec] = DEFAULT_ROUTE_SPECS,
    workflow: str = "public",
) -> dict[str, object]:
    thresholds = PerformanceThresholds()
    routes = tuple(route_specs)
    return {
        "mode": "contract_only",
        "workflow": workflow,
        "browser_requirement": "playwright plus a local chrome-compatible executable",
        "demo_snapshot": demo_snapshot_identity(base_dir),
        "routes": [asdict(route) for route in routes],
        "viewports": [asdict(viewport) for viewport in DEFAULT_VIEWPORTS],
        "thresholds": asdict(thresholds),
        "boundary": (
            "Read-only performance evidence: does not refresh data, apply imports, stage files, commit, push, "
            "provide investment advice, connect to brokers, route orders, or enable auto-trading."
        ),
    }


def _browser_unavailable_payload(
    base_dir: Path | str | None = None,
    *,
    route_specs: Iterable[PublicRouteSpec] = DEFAULT_ROUTE_SPECS,
    workflow: str = "public",
) -> dict[str, object]:
    payload = performance_contract_payload(base_dir, route_specs=route_specs, workflow=workflow)
    payload.update(
        {
            "mode": "browser",
            "verdict": "environment_limited",
            "detail": "The optional Playwright dependency is unavailable; no browser timings were recorded.",
            "next": (
                "Install the development dependency, then rerun make commercial-beta-performance-gate."
                if workflow == "research"
                else "Install the development dependency, then rerun make public-performance-gate."
            ),
        }
    )
    return payload


def _git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, *, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    health_url = f"{base_url.rstrip('/')}/_stcore/health"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # pragma: no cover - depends on process startup timing
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Streamlit health check did not become ready: {last_error}")


@contextlib.contextmanager
def _local_demo_server(root: Path, *, port: int | None = None, timeout_seconds: float = 45.0):
    selected_port = port or _free_port()
    base_url = f"http://127.0.0.1:{selected_port}"
    env = os.environ.copy()
    env["STOCK_RESEARCH_DATA_PROFILE"] = "demo"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/dashboard.py",
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
            "--client.toolbarMode",
            "viewer",
            "--server.port",
            str(selected_port),
        ],
        cwd=root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        _wait_for_health(base_url, timeout_seconds=timeout_seconds)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive process cleanup
            process.kill()
            process.wait(timeout=5)


def _wait_for_dom_stability(page, *, timeout_seconds: float, stable_checks: int = 3) -> None:
    deadline = time.monotonic() + timeout_seconds
    previous: tuple[int, str] | None = None
    stable = 0
    while time.monotonic() < deadline:
        text = page.locator("body").inner_text(timeout=2_000)
        current = (len(text), text[-500:])
        visible_spinners = page.locator('[data-testid="stSpinner"]').count()
        if current == previous and visible_spinners == 0:
            stable += 1
            if stable >= stable_checks:
                return
        else:
            stable = 0
        previous = current
        page.wait_for_timeout(250)
    raise TimeoutError("route DOM did not settle before the timeout")


def _wait_for_visible_text(page, marker: str, *, timeout_seconds: float) -> None:
    try:
        page.wait_for_function(
            "(marker) => document.body && document.body.innerText.includes(marker)",
            arg=marker,
            timeout=int(timeout_seconds * 1000),
        )
    except Exception as exc:
        url = str(getattr(page, "url", "unavailable") or "unavailable")
        try:
            body = page.locator("body").inner_text(timeout=2_000)
        except Exception:
            body = "visible body unavailable"
        body_snapshot = " ".join(str(body or "").split())[:1_000] or "visible body empty"
        raise TimeoutError(
            f"visible marker not found before timeout: {marker}; "
            f"url={url}; visible_body={body_snapshot!r}"
        ) from exc


def _horizontal_overflow_pixels(page) -> int:
    value = page.evaluate(
        "Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"
    )
    return max(0, int(value or 0))


def _measure_route(
    browser,
    *,
    base_url: str,
    route: PublicRouteSpec,
    viewport: Viewport,
    run_kind: str,
    timeout_seconds: float,
) -> RouteTimingSample:
    context = browser.new_context(viewport={"width": viewport.width, "height": viewport.height})
    page = context.new_page()
    started = time.perf_counter()
    shell_seconds: float | None = None
    first_useful_seconds: float | None = None
    full_settle_seconds: float | None = None
    try:
        page.goto(
            f"{base_url.rstrip('/')}{route.route}",
            wait_until="domcontentloaded",
            timeout=int(timeout_seconds * 1000),
        )
        page.locator('[data-testid="stAppViewContainer"]').wait_for(
            state="visible",
            timeout=int(timeout_seconds * 1000),
        )
        shell_seconds = time.perf_counter() - started
        _wait_for_visible_text(page, route.first_useful_marker, timeout_seconds=timeout_seconds)
        first_useful_seconds = time.perf_counter() - started
        for marker in route.full_markers:
            _wait_for_visible_text(page, marker, timeout_seconds=timeout_seconds)
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
        overflow_pixels = _horizontal_overflow_pixels(page)
        if overflow_pixels > 1:
            raise RuntimeError(f"horizontal overflow: {overflow_pixels}px")
        full_settle_seconds = time.perf_counter() - started
        return RouteTimingSample(
            route.name,
            viewport.label,
            run_kind,
            shell_seconds,
            first_useful_seconds,
            full_settle_seconds,
            True,
        )
    except Exception as exc:  # browser failures become evidence, not crashes
        return RouteTimingSample(
            route.name,
            viewport.label,
            run_kind,
            shell_seconds,
            first_useful_seconds,
            full_settle_seconds,
            False,
            f"{type(exc).__name__}: {exc}",
        )
    finally:
        context.close()
        time.sleep(0.25)


def run_browser_performance_gate(
    base_dir: Path | str | None = None,
    *,
    warm_runs: int = 5,
    cold_runs: int = 1,
    timeout_seconds: float = 30.0,
    base_url: str = "",
    chrome_executable: Path | None = None,
    progress: Callable[[str], None] | None = None,
    route_specs: Iterable[PublicRouteSpec] = DEFAULT_ROUTE_SPECS,
    workflow: str = "public",
) -> dict[str, object]:
    root = resolve_project_root(base_dir)
    routes = tuple(route_specs)
    chrome = chrome_executable or find_chrome_executable()
    if chrome is None:
        payload = _browser_unavailable_payload(root, route_specs=routes, workflow=workflow)
        payload["detail"] = "No executable Chrome-compatible browser was found; no timings were recorded."
        return payload

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _browser_unavailable_payload(root, route_specs=routes, workflow=workflow)

    samples: list[RouteTimingSample] = []
    total_samples = len(routes) * len(DEFAULT_VIEWPORTS) * (cold_runs + warm_runs)

    def record(sample: RouteTimingSample) -> None:
        samples.append(sample)
        if progress is not None:
            progress(performance_progress_line(sample, index=len(samples), total=total_samples))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            if cold_runs:
                for route in routes:
                    for viewport in DEFAULT_VIEWPORTS:
                        for _ in range(cold_runs):
                            if base_url:
                                record(
                                    _measure_route(
                                        browser,
                                        base_url=base_url,
                                        route=route,
                                        viewport=viewport,
                                        run_kind="cold",
                                        timeout_seconds=timeout_seconds,
                                    )
                                )
                            else:
                                with _local_demo_server(root, timeout_seconds=timeout_seconds) as local_url:
                                    record(
                                        _measure_route(
                                            browser,
                                            base_url=local_url,
                                            route=route,
                                            viewport=viewport,
                                            run_kind="cold",
                                            timeout_seconds=timeout_seconds,
                                        )
                                    )

            if warm_runs:
                server_context = contextlib.nullcontext(base_url) if base_url else _local_demo_server(
                    root,
                    timeout_seconds=timeout_seconds,
                )
                with server_context as active_url:
                    for route in routes:
                        for viewport in DEFAULT_VIEWPORTS:
                            _measure_route(
                                browser,
                                base_url=active_url,
                                route=route,
                                viewport=viewport,
                                run_kind="warmup",
                                timeout_seconds=timeout_seconds,
                            )
                            for _ in range(warm_runs):
                                record(
                                    _measure_route(
                                        browser,
                                        base_url=active_url,
                                        route=route,
                                        viewport=viewport,
                                        run_kind="warm",
                                        timeout_seconds=timeout_seconds,
                                    )
                                )
        finally:
            browser.close()

    return performance_result_payload(
        root,
        samples,
        commit=_git_commit(root),
        environment=f"{platform.system()} {platform.machine()} | Chrome: {chrome}",
        critical_routes={route.name for route in routes if route.critical},
        workflow=workflow,
        min_warm_runs=warm_runs,
        min_cold_runs=cold_runs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure the guided public workflow against explicit performance gates.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--contract", action="store_true", help="Print the read-only route and threshold contract.")
    mode.add_argument("--browser", action="store_true", help="Run the optional real-browser performance gate.")
    parser.add_argument("--root", default=".", help="Project root containing data/demo/manifest.json.")
    parser.add_argument(
        "--workflow",
        choices=("public", "research"),
        default="public",
        help="Route workflow to measure.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    parser.add_argument("--warm-runs", type=int, default=5, help="Recorded warm runs per route and viewport.")
    parser.add_argument("--cold-runs", type=int, default=1, help="Recorded cold runs per route and viewport.")
    parser.add_argument("--timeout-seconds", type=float, default=30.0, help="Per-route and local-start timeout.")
    parser.add_argument("--base-url", default="", help="Optional already-running local or hosted base URL.")
    parser.add_argument("--chrome", default="", help="Optional Chrome-compatible executable path.")
    parser.add_argument(
        "--output",
        default="/tmp/stock-command-center-public-performance.json",
        help="Generated JSON evidence path; keep it out of staging by default.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    route_specs = RESEARCH_ROUTE_SPECS if args.workflow == "research" else DEFAULT_ROUTE_SPECS
    if args.browser:
        payload = run_browser_performance_gate(
            root,
            warm_runs=max(0, args.warm_runs),
            cold_runs=max(0, args.cold_runs),
            timeout_seconds=max(1.0, args.timeout_seconds),
            base_url=args.base_url,
            chrome_executable=Path(args.chrome) if args.chrome else None,
            progress=lambda line: print(line, file=sys.stderr, flush=True),
            route_specs=route_specs,
            workflow=args.workflow,
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        if payload.get("verdict") == "passed":
            return 0
        if payload.get("verdict") == "environment_limited":
            return 2
        return 1

    payload = performance_contract_payload(root, route_specs=route_specs, workflow=args.workflow)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        title = "Commercial Beta Performance Contract" if args.workflow == "research" else "Public Performance Contract"
        print(title)
        print(payload["boundary"])
        print(f"Demo snapshot: {payload['demo_snapshot']['sha256']}")
        for route in route_specs:
            critical = "critical" if route.critical else "regression"
            print(f"- {route.name}: {critical} | {route.route} | first useful: {route.first_useful_marker}")
        print("Thresholds:")
        for key, value in payload["thresholds"].items():
            print(f"- {key}: {value:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
