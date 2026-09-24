"""
In-memory sliding-window rate limiter for AI Jailbreak Arena.

Implements Issue #3: [Backend] Sliding-Window 3-Second Rate Limiter.
References:
- docs/PRD.md §4 (Rate Limiting & Protections) & §6 (Complete Backend Implementation)
- docs/SAD.md §2.2 (Per-Host Throttling)
- docs/TECH-SPEC.md §1.1 (Sequence Diagram) & §2.2 (Status Codes)
"""

import time
from typing import Annotated, Callable, Optional

from fastapi import Depends, HTTPException, status

from app.config import Settings, get_settings


class SlidingWindowRateLimiter:
    """
    Per-user sliding-window rate limiter enforcing a cooldown between requests.

    Maintains an in-memory dictionary of last-request timestamps per user_id.
    Rejects requests arriving within < cooldown_seconds with HTTP 429.
    """

    def __init__(
        self,
        cooldown_seconds: float = 3.0,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.time_func = time_func
        self._last_request: dict[str, float] = {}

    def check(self, user_id: str) -> None:
        """
        Check if the participant is on cooldown.

        Raises HTTPException(429) if elapsed time since last accepted request < cooldown_seconds.
        Does not mutate the timestamp so that rejected requests do not penalize the user
        or reset the cooldown timer.
        """
        last_time = self._last_request.get(user_id)
        if last_time is not None:
            now = self.time_func()
            elapsed = now - last_time
            if elapsed < self.cooldown_seconds:
                remaining = self.cooldown_seconds - elapsed
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit: Wait {remaining:.1f}s",
                    headers={"Retry-After": str(max(1, int(round(remaining))))},
                )

    def update(self, user_id: str) -> None:
        """Record current timestamp as the user's latest accepted request."""
        now = self.time_func()
        self._last_request[user_id] = now

        # Lightweight periodic cleanup if dictionary grows large
        if len(self._last_request) > 1000:
            self._prune(now)

    def check_and_update(self, user_id: str) -> None:
        """Atomic check and update for a user request."""
        self.check(user_id)
        self.update(user_id)

    def get_remaining(self, user_id: str) -> float:
        """Return remaining cooldown seconds for user, or 0.0 if not on cooldown."""
        last_time = self._last_request.get(user_id)
        if last_time is None:
            return 0.0
        elapsed = self.time_func() - last_time
        return max(0.0, self.cooldown_seconds - elapsed)

    def reset(self, user_id: Optional[str] = None) -> None:
        """Reset rate limiter state for a specific user, or all users if None."""
        if user_id is not None:
            self._last_request.pop(user_id, None)
        else:
            self._last_request.clear()

    def _prune(self, now: float) -> None:
        """Prune timestamps older than 2x cooldown to prevent memory leaks."""
        cutoff = now - (self.cooldown_seconds * 2)
        stale_keys = [k for k, v in self._last_request.items() if v < cutoff]
        for k in stale_keys:
            del self._last_request[k]


_global_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter(
    settings: Annotated[Optional[Settings], Depends(get_settings)] = None,
) -> SlidingWindowRateLimiter:
    """FastAPI dependency providing the active SlidingWindowRateLimiter."""
    global _global_limiter
    cooldown = settings.COOLDOWN_SECONDS if settings else 3.0
    if _global_limiter is None:
        _global_limiter = SlidingWindowRateLimiter(cooldown_seconds=cooldown)
    elif settings and _global_limiter.cooldown_seconds != settings.COOLDOWN_SECONDS:
        _global_limiter.cooldown_seconds = settings.COOLDOWN_SECONDS
    return _global_limiter
