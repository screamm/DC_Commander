# DC Commander - Performance Benchmarks

Directory-listing benchmarks that exercise the `DirectoryCache` and a render-proxy
equivalent to what `FilePanel` does when the user navigates.

## How to run

```bash
# Fast tier only (1k + 10k scenarios)
pytest tests/perf/ -m "not slow"

# Full sweep including 50k (slow)
pytest tests/perf/

# With pytest-benchmark harness (if installed)
pytest tests/perf/ --benchmark-only

# Quiet output without coverage noise
pytest tests/perf/ -v --no-cov -m "not slow"
```

## Targets (Sprint 3 plan)

| Scenario | Files  | Target     | Marked slow? |
|----------|-------:|------------|--------------|
| 1k       |  1 000 |  < 200 ms  | no           |
| 10k      | 10 000 |  < 2 s     | no           |
| 50k      | 50 000 |  < 10 s    | yes          |

Each scenario measures: `os.scandir` enumeration + `stat` per entry + sort by
`(is_dir, name)`. That sequence approximates what `FilePanel._load_directory`
does and what `DirectoryCache` stores.

## Interpreting results

* Thresholds are based on sprint planning, not on profiling the real UI. Treat
  failures as **baselines to improve against**, not blocking regressions.
* The `perf` CI job is marked `continue-on-error: true` until thresholds are
  calibrated post-v1.0.
* `DirectoryCache` warm-hit tests verify the cache provides a material speedup
  over a cold scan — the absolute numbers vary by host.

## When to add a scenario

* New production code path that enumerates a directory.
* Changes to `DirectoryCache` invalidation or TTL logic.
* Regressions reported from users running on slow storage (network mounts,
  fuse filesystems).

Keep scenarios self-contained (session-scoped `tmp_path_factory`), deterministic,
and cheap to set up — each must create its dataset once per session.
