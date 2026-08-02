"""Thread-safe cache performance metrics for EcoBuddy AI."""

from __future__ import annotations

from collections import defaultdict
import threading
import time


class CacheMetrics:
    """Collect fresh/stale cache and refresh lifecycle counters."""

    _COUNTERS = (
        "fresh_hits",
        "stale_hits",
        "misses",
        "invalidations",
        "refreshes",
        "refresh_failures",
        "prevented_duplicate_computations",
    )

    def __init__(self):
        self._lock = threading.Lock()
        self._values = {
            name: defaultdict(int)
            for name in self._COUNTERS
        }
        self._last_reset = time.time()

    def _record(self, counter, cache_name):
        with self._lock:
            self._values[counter][cache_name] += 1

    def record_fresh_hit(self, cache_name):
        self._record("fresh_hits", cache_name)

    def record_stale_hit(self, cache_name):
        self._record("stale_hits", cache_name)

    def record_miss(self, cache_name):
        self._record("misses", cache_name)

    def record_invalidation(self, cache_name):
        self._record("invalidations", cache_name)

    def record_refresh(self, cache_name):
        self._record("refreshes", cache_name)

    def record_refresh_failure(self, cache_name):
        self._record("refresh_failures", cache_name)

    def record_prevented_duplicate(self, cache_name):
        self._record(
            "prevented_duplicate_computations",
            cache_name,
        )

    def get_stats(self, cache_name=None):
        with self._lock:
            names = set()
            for counter in self._COUNTERS:
                names.update(self._values[counter].keys())

            def stats_for(name):
                fresh = self._values["fresh_hits"].get(name, 0)
                stale = self._values["stale_hits"].get(name, 0)
                misses = self._values["misses"].get(name, 0)
                total = fresh + stale + misses
                return {
                    "hits": fresh + stale,
                    "fresh_hits": fresh,
                    "stale_hits": stale,
                    "misses": misses,
                    "invalidations": self._values[
                        "invalidations"
                    ].get(name, 0),
                    "refreshes": self._values[
                        "refreshes"
                    ].get(name, 0),
                    "refresh_failures": self._values[
                        "refresh_failures"
                    ].get(name, 0),
                    "prevented_duplicate_computations": self._values[
                        "prevented_duplicate_computations"
                    ].get(name, 0),
                    "hit_rate": round(
                        ((fresh + stale) / total * 100)
                        if total
                        else 0.0,
                        1,
                    ),
                }

            if cache_name is not None:
                return stats_for(cache_name)

            per_cache = {
                name: stats_for(name)
                for name in sorted(names)
            }
            totals = {
                counter: sum(self._values[counter].values())
                for counter in self._COUNTERS
            }
            hits = totals["fresh_hits"] + totals["stale_hits"]
            total_requests = hits + totals["misses"]
            return {
                "hits": hits,
                **totals,
                "hit_rate": round(
                    (hits / total_requests * 100)
                    if total_requests
                    else 0.0,
                    1,
                ),
                "per_cache": per_cache,
            }

    def reset(self):
        with self._lock:
            for values in self._values.values():
                values.clear()
            self._last_reset = time.time()


_metrics = CacheMetrics()


def record_hit(cache_name):
    """Backward-compatible alias for a fresh cache hit."""
    _metrics.record_fresh_hit(cache_name)


def record_fresh_hit(cache_name):
    _metrics.record_fresh_hit(cache_name)


def record_stale_hit(cache_name):
    _metrics.record_stale_hit(cache_name)


def record_miss(cache_name):
    _metrics.record_miss(cache_name)


def record_invalidation(cache_name):
    _metrics.record_invalidation(cache_name)


def record_refresh(cache_name):
    _metrics.record_refresh(cache_name)


def record_refresh_failure(cache_name):
    _metrics.record_refresh_failure(cache_name)


def record_prevented_duplicate(cache_name):
    _metrics.record_prevented_duplicate(cache_name)


def get_cache_stats(cache_name=None):
    return _metrics.get_stats(cache_name)


def get_all_cache_stats():
    return _metrics.get_stats()


def reset_metrics():
    _metrics.reset()


def render_metrics_sidebar():
    """Render cache metrics in Streamlit's sidebar."""
    import streamlit as st

    stats = get_all_cache_stats()
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Cache Metrics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Fresh", stats["fresh_hits"])
        col2.metric("Stale", stats["stale_hits"])
        col3.metric("Hit Rate", f'{stats["hit_rate"]}%')

        st.caption(
            f'Refreshes: {stats["refreshes"]} · '
            f'Failures: {stats["refresh_failures"]} · '
            "Duplicates prevented: "
            f'{stats["prevented_duplicate_computations"]}'
        )

        if stats["per_cache"]:
            with st.expander("Per-Cache Breakdown"):
                for name, data in stats["per_cache"].items():
                    st.text(
                        f"{name}: {data['fresh_hits']} fresh / "
                        f"{data['stale_hits']} stale / "
                        f"{data['misses']} miss"
                    )
