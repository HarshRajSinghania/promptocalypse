"""
Health & readiness probe helpers: SQLite database verification and a cached
upstream provider connectivity check.

Implements Issue #26: [Backend] Health & Readiness Diagnostic Probe (/api/health).
References:
- docs/TECH-SPEC.md §3 — Database Specification (SQLite WAL & PRAGMAs).
- docs/TECH-SPEC.md §6 — Upstream Inference Service Client Specification.

Design mirrors app/rate_limiter.py: a plain class with an injectable clock
(``time_func``), exposed to routes through a FastAPI dependency that returns a
module-level singleton. Unit tests can therefore override the cache via
``app.dependency_overrides[get_provider_health_cache]`` and advance a
simulated clock instead of waiting in real time.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Optional

from app.config import Settings
from app.database import get_db_context

# Upstream provider identity reported in the health payload.
PROVIDER_NAME = "groq"

# Provider probe cache lifetime — exactly 60 seconds (Issue #26).
PROVIDER_CACHE_TTL_SECONDS = 60.0

# Short timeout for the provider probe. Deliberately far below the 8-second
# chat inference timeout; matches the 3.0s connect timeout budget from
# docs/TECH-SPEC.md §6.2 so health probes never hang the readiness check.
PROVIDER_PROBE_TIMEOUT_SECONDS = 3.0


def utc_now_iso() -> str:
    """ISO 8601 UTC timestamp with millisecond precision (logger format)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


async def check_database() -> dict:
    """
    Verify SQLite connectivity, WAL journal mode, and query execution.

    Opens a fresh connection through the existing ``get_db_context()``
    infrastructure (which applies the WAL PRAGMAs on every connection), runs
    ``SELECT 1``, confirms ``PRAGMA journal_mode`` reports ``wal``, and
    measures end-to-end latency in milliseconds.

    Never raises — all failures are reported in the returned mapping so the
    health endpoint can render a structured 503 response instead.
    """
    start = time.perf_counter()
    try:
        async with get_db_context() as db:
            cursor = await db.execute("SELECT 1")
            row = await cursor.fetchone()
            cursor = await db.execute("PRAGMA journal_mode")
            journal_row = await cursor.fetchone()

        latency_ms = int((time.perf_counter() - start) * 1000)
        journal_mode = str(journal_row[0]).lower() if journal_row else None
        select_ok = row is not None and row[0] == 1
        wal_ok = journal_mode == "wal"

        if select_ok and wal_ok:
            return {
                "status": "ok",
                "latency_ms": latency_ms,
                "journal_mode": journal_mode,
                "error": None,
            }
        return {
            "status": "error",
            "latency_ms": latency_ms,
            "journal_mode": journal_mode,
            "error": "SELECT 1 failed" if not select_ok else "journal_mode is not 'wal'",
        }
    except Exception as exc:  # Database unavailable (bad path, locked, missing...)
        return {
            "status": "error",
            "latency_ms": None,
            "journal_mode": None,
            "error": str(exc) or exc.__class__.__name__,
        }


class ProviderHealthCache:
    """
    Caches the result of the upstream Groq connectivity probe for exactly
    ``ttl_seconds`` (60s by default).

    Fresh hits return the stored snapshot with ``cached=True`` and the
    original ``checked_at`` timestamp without touching the network. Expired
    (or first) calls run the probe once and refresh the snapshot. Probe
    failures are cached too so a downed provider is not hammered by polling.
    An empty ``GROQ_API_KEY`` short-circuits to an ``unconfigured`` state
    without ever calling upstream.
    """

    def __init__(
        self,
        ttl_seconds: float = PROVIDER_CACHE_TTL_SECONDS,
        time_func=time.monotonic,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.time_func = time_func
        self._snapshot: Optional[dict] = None
        self._checked_at_mono: Optional[float] = None

    def get_cached(self) -> Optional[dict]:
        """Return the cached snapshot if still fresh, otherwise None."""
        if self._snapshot is None or self._checked_at_mono is None:
            return None
        if self.time_func() - self._checked_at_mono >= self.ttl_seconds:
            return None
        return self._snapshot

    async def probe(
        self,
        client,
        settings: Settings,
        timeout_seconds: float = PROVIDER_PROBE_TIMEOUT_SECONDS,
    ) -> dict:
        """
        Return the provider health snapshot, probing upstream only on cache miss.

        The probe is a lightweight authenticated ``models.list()`` call (no
        tokens consumed) wrapped in a short ``asyncio.wait_for`` timeout.
        """
        cached = self.get_cached()
        if cached is not None:
            return {**cached, "cached": True}

        # Unconfigured provider: no API key → never call upstream.
        if not settings.GROQ_API_KEY:
            snapshot = {
                "status": "unconfigured",
                "latency_ms": None,
                "error": "GROQ_API_KEY is not configured",
                "checked_at": utc_now_iso(),
            }
            self._store(snapshot)
            return {**snapshot, "cached": False}

        start = time.perf_counter()
        try:
            await asyncio.wait_for(client.models.list(), timeout=timeout_seconds)
            status, error = "ok", None
        except (asyncio.TimeoutError, TimeoutError):
            status = "error"
            error = f"Provider probe timed out after {timeout_seconds:g}s"
        except Exception as exc:
            status = "error"
            error = str(exc) or exc.__class__.__name__

        snapshot = {
            "status": status,
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "error": error,
            "checked_at": utc_now_iso(),
        }
        self._store(snapshot)
        return {**snapshot, "cached": False}

    def _store(self, snapshot: dict) -> None:
        self._snapshot = snapshot
        self._checked_at_mono = self.time_func()

    def clear(self) -> None:
        """Drop any cached snapshot (useful for testing)."""
        self._snapshot = None
        self._checked_at_mono = None


_global_provider_health_cache: Optional[ProviderHealthCache] = None


def get_provider_health_cache() -> ProviderHealthCache:
    """FastAPI dependency providing the shared provider health cache."""
    global _global_provider_health_cache
    if _global_provider_health_cache is None:
        _global_provider_health_cache = ProviderHealthCache()
    return _global_provider_health_cache
