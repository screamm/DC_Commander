"""Performance benchmarks for directory listing (Sprint 3 S3.5).

Measures directory scan + render-proxy time for scenarios at 1k, 10k, and 50k
flat files. Targets (from Sprint 3 plan):

    1 000 files:  scan + render proxy  < 200 ms
   10 000 files:  scan + render proxy  < 2 s
   50 000 files:  scan + render proxy  < 10 s   (marked ``slow``)

Uses ``pytest-benchmark`` when available; otherwise falls back to plain
``time.perf_counter`` and asserts against the same thresholds with a
custom summary line printed via ``-s``.

Run
---
    pytest tests/perf/ -m "not slow"   # 1k + 10k
    pytest tests/perf/                  # all scenarios
    pytest tests/perf/ --benchmark-only # only when pytest-benchmark present
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Callable, List, Tuple

import pytest

# --------------------------------------------------------------------------- #
# Optional pytest-benchmark integration
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - import guard only
    import pytest_benchmark  # noqa: F401
    HAVE_BENCHMARK = True
except ImportError:  # pragma: no cover
    HAVE_BENCHMARK = False


# --------------------------------------------------------------------------- #
# DirectoryCache is the production cache under test.  Import read-only.
# --------------------------------------------------------------------------- #
from src.utils.directory_cache import DirectoryCache  # noqa: E402


# --------------------------------------------------------------------------- #
# Scenario configuration
# --------------------------------------------------------------------------- #
SCENARIOS: List[Tuple[str, int, float, bool]] = [
    # (label, file_count, threshold_seconds, is_slow)
    ("1k", 1_000, 0.200, False),
    ("10k", 10_000, 2.000, False),
    ("50k", 50_000, 10.000, True),
]


# --------------------------------------------------------------------------- #
# Session-scoped fixtures create each dataset once
# --------------------------------------------------------------------------- #
def _materialise_flat_dir(root: Path, count: int) -> Path:
    """Create ``count`` empty files in ``root`` and return it.

    Uses ``open`` rather than ``Path.touch`` for a small speedup when
    count is large.  Returns the root so the caller can point a scanner
    at it.
    """
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        # Fixed-width name keeps sort order deterministic for the render-proxy
        fname = f"file_{i:06d}.txt"
        (root / fname).write_bytes(b"")
    return root


@pytest.fixture(scope="session")
def dir_1k(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _materialise_flat_dir(tmp_path_factory.mktemp("perf_1k"), 1_000)


@pytest.fixture(scope="session")
def dir_10k(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _materialise_flat_dir(tmp_path_factory.mktemp("perf_10k"), 10_000)


@pytest.fixture(scope="session")
def dir_50k(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _materialise_flat_dir(tmp_path_factory.mktemp("perf_50k"), 50_000)


# --------------------------------------------------------------------------- #
# Workload: simulates what FilePanel does on directory change
# --------------------------------------------------------------------------- #
def _scan_and_render_proxy(path: Path) -> int:
    """Scan directory and build a sort-stable render list.

    This approximates the FilePanel workflow without depending on the
    Textual widget layer:

    1.  ``os.scandir`` to enumerate entries (what the cache loader does).
    2.  Capture ``stat`` info for each entry (size, mtime).
    3.  Sort by (is_dir desc, name asc) - matches FilePanel default order.

    Returns the number of entries processed so the benchmark harness has
    a concrete value to assert against.
    """
    rows: List[Tuple[bool, str, int, float]] = []
    with os.scandir(path) as it:
        for entry in it:
            try:
                st = entry.stat(follow_symlinks=False)
                rows.append(
                    (entry.is_dir(follow_symlinks=False), entry.name, st.st_size, st.st_mtime)
                )
            except OSError:
                # Skip inaccessible entries, same policy as FilePanel.
                continue

    rows.sort(key=lambda r: (not r[0], r[1].lower()))
    return len(rows)


def _cached_scan_and_render(cache: DirectoryCache, path: Path) -> int:
    """Same workload but routed through DirectoryCache.get_or_load."""

    def loader(p: Path) -> List[Tuple[bool, str, int, float]]:
        rows: List[Tuple[bool, str, int, float]] = []
        with os.scandir(p) as it:
            for entry in it:
                try:
                    st = entry.stat(follow_symlinks=False)
                    rows.append(
                        (
                            entry.is_dir(follow_symlinks=False),
                            entry.name,
                            st.st_size,
                            st.st_mtime,
                        )
                    )
                except OSError:
                    continue
        rows.sort(key=lambda r: (not r[0], r[1].lower()))
        return rows

    data = cache.get_or_load(path, loader)
    return len(data)


# --------------------------------------------------------------------------- #
# Helper: time a callable with perf_counter when pytest-benchmark absent
# --------------------------------------------------------------------------- #
def _time_call(fn: Callable[[], int], repeats: int = 3) -> Tuple[float, int]:
    """Run ``fn`` ``repeats`` times and return ``(best_seconds, result)``."""
    best = float("inf")
    result = 0
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = fn()
        dt = time.perf_counter() - t0
        if dt < best:
            best = dt
    return best, result


# --------------------------------------------------------------------------- #
# Scan-only benchmarks
# --------------------------------------------------------------------------- #
class TestScanRenderProxy:
    """Scan + render proxy without cache - raw filesystem throughput."""

    def test_1k_scan_render(self, dir_1k: Path, request: pytest.FixtureRequest) -> None:
        threshold = 0.200
        if HAVE_BENCHMARK and request.config.getoption("--benchmark-only", default=False):
            benchmark = request.getfixturevalue("benchmark")
            count = benchmark(_scan_and_render_proxy, dir_1k)
            assert count == 1_000
        else:
            best, count = _time_call(lambda: _scan_and_render_proxy(dir_1k))
            print(f"\n[perf] 1k scan+render: {best * 1000:.1f} ms (target <{threshold * 1000:.0f} ms)")
            assert count == 1_000
            assert best < threshold, (
                f"1k scan+render took {best * 1000:.1f} ms, exceeds {threshold * 1000:.0f} ms target"
            )

    def test_10k_scan_render(self, dir_10k: Path, request: pytest.FixtureRequest) -> None:
        threshold = 2.000
        if HAVE_BENCHMARK and request.config.getoption("--benchmark-only", default=False):
            benchmark = request.getfixturevalue("benchmark")
            count = benchmark(_scan_and_render_proxy, dir_10k)
            assert count == 10_000
        else:
            best, count = _time_call(lambda: _scan_and_render_proxy(dir_10k), repeats=2)
            print(f"\n[perf] 10k scan+render: {best * 1000:.1f} ms (target <{threshold * 1000:.0f} ms)")
            assert count == 10_000
            assert best < threshold, (
                f"10k scan+render took {best * 1000:.1f} ms, exceeds {threshold * 1000:.0f} ms target"
            )

    @pytest.mark.slow
    def test_50k_scan_render(self, dir_50k: Path, request: pytest.FixtureRequest) -> None:
        threshold = 10.000
        if HAVE_BENCHMARK and request.config.getoption("--benchmark-only", default=False):
            benchmark = request.getfixturevalue("benchmark")
            count = benchmark(_scan_and_render_proxy, dir_50k)
            assert count == 50_000
        else:
            best, count = _time_call(lambda: _scan_and_render_proxy(dir_50k), repeats=1)
            print(f"\n[perf] 50k scan+render: {best * 1000:.1f} ms (target <{threshold * 1000:.0f} ms)")
            assert count == 50_000
            assert best < threshold, (
                f"50k scan+render took {best * 1000:.1f} ms, exceeds {threshold * 1000:.0f} ms target"
            )


# --------------------------------------------------------------------------- #
# DirectoryCache benchmarks - measure cache-hit path
# --------------------------------------------------------------------------- #
class TestDirectoryCacheLoad:
    """DirectoryCache cold-load and warm-hit performance."""

    def test_1k_cache_cold_load(self, dir_1k: Path) -> None:
        cache = DirectoryCache(maxsize=16, ttl_seconds=60)
        best, count = _time_call(lambda: _cached_scan_and_render(cache, dir_1k), repeats=1)
        # Cold load is dominated by scan; soft threshold
        print(f"\n[perf] 1k cache cold load: {best * 1000:.1f} ms")
        assert count == 1_000

    def test_1k_cache_warm_hit(self, dir_1k: Path) -> None:
        cache = DirectoryCache(maxsize=16, ttl_seconds=60)
        # Warm the cache
        _cached_scan_and_render(cache, dir_1k)

        # Measure the warm-hit path - should be effectively free
        best, count = _time_call(lambda: _cached_scan_and_render(cache, dir_1k), repeats=5)
        print(f"\n[perf] 1k cache warm hit: {best * 1_000_000:.1f} us")
        assert count == 1_000
        # Warm hit should be far under the cold threshold
        assert best < 0.050, f"Warm cache hit took {best * 1000:.1f} ms, expected <50 ms"

    def test_10k_cache_warm_hit(self, dir_10k: Path) -> None:
        cache = DirectoryCache(maxsize=16, ttl_seconds=60)
        _cached_scan_and_render(cache, dir_10k)

        best, count = _time_call(lambda: _cached_scan_and_render(cache, dir_10k), repeats=5)
        print(f"\n[perf] 10k cache warm hit: {best * 1_000_000:.1f} us")
        assert count == 10_000
        assert best < 0.100, f"Warm cache hit took {best * 1000:.1f} ms, expected <100 ms"
