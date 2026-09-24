"""
Health & readiness diagnostic probe route.

Implements Issue #26: [Backend] Health & Readiness Diagnostic Probe (/api/health).
References:
- docs/TECH-SPEC.md §3 — Database Specification (SQLite WAL & PRAGMAs).
- docs/TECH-SPEC.md §6 — Upstream Inference Service Client Specification.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Response
import openai

from app.config import Settings, get_settings
from app.health import (
    PROVIDER_NAME,
    ProviderHealthCache,
    check_database,
    get_provider_health_cache,
    utc_now_iso,
)
from app.logger import logger
from app.models import HealthDatabaseStatus, HealthProviderStatus, HealthResponse
from app.routes.chat import get_groq_client

router = APIRouter(prefix="/api", tags=["health"])


# Overall status of the previous probe. Transitions are logged once;
# steady-state probes stay silent so periodic health polling cannot flood
# the telemetry log or the warning/error ring buffer (Issue #26).
_last_reported_status: Optional[str] = None


def reset_health_status_logging() -> None:
    """Reset the transition tracker (useful for testing)."""
    global _last_reported_status
    _last_reported_status = None


def _maybe_log_status_transition(
    overall_status: str,
    database_status: str,
    provider_status: str,
) -> None:
    """Log a structured event only when the overall health status changes."""
    global _last_reported_status
    if overall_status == _last_reported_status:
        return
    previous_status = _last_reported_status
    _last_reported_status = overall_status

    extra = {
        "event": "health_status_change",
        "previous_status": previous_status,
        "status": overall_status,
        "database_status": database_status,
        "provider_status": provider_status,
    }
    if overall_status == "ok":
        logger.info("Health probe status changed", extra=extra)
    else:
        logger.warning("Health probe status changed", extra=extra)


@router.get("/health", response_model=HealthResponse)
async def health_diagnostic(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[openai.AsyncOpenAI, Depends(get_groq_client)],
    health_cache: Annotated[ProviderHealthCache, Depends(get_provider_health_cache)],
) -> HealthResponse:
    """
    Health & readiness diagnostic probe (Issue #26).

    - Database: opens the standard SQLite/WAL connection, runs ``SELECT 1``,
      verifies ``journal_mode = wal``, and measures latency.
    - Provider: pings the Groq upstream with a short timeout; the result is
      cached for exactly 60 seconds to avoid hammering the provider. An empty
      ``GROQ_API_KEY`` reports an ``unconfigured`` state without a network call.

    Status codes:
    - 503: database unavailable (service not ready).
    - 200: database healthy — overall ``ok`` when the provider is healthy,
      ``degraded`` when the provider failed or is unconfigured.
    """
    database = await check_database()
    provider = await health_cache.probe(client, settings)

    database_ok = database["status"] == "ok"
    if not database_ok:
        overall_status = "error"
        response.status_code = 503
    elif provider["status"] == "ok":
        overall_status = "ok"
    else:
        overall_status = "degraded"

    _maybe_log_status_transition(overall_status, database["status"], provider["status"])

    return HealthResponse(
        status=overall_status,
        database=HealthDatabaseStatus(**database),
        provider=HealthProviderStatus(
            status=provider["status"],
            name=PROVIDER_NAME,
            model=settings.GROQ_MODEL,
            latency_ms=provider["latency_ms"],
            cached=provider["cached"],
            checked_at=provider["checked_at"],
            error=provider["error"],
        ),
        timestamp=utc_now_iso(),
    )
