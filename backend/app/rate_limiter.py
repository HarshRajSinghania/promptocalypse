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

class KeySubmissionRateLimiter:
    """
    Independent rate-limiter for /api/submit-key (Issue #43).
    - Base cooldown: 2.0 seconds between any submission attempts.
    - Escalating penalty: After 3 failed key submissions in a row, enforces a 30-second lockout.
    """

    def __init__(
        self,
        base_cooldown: float = 2.0,
        lockout_duration: float = 30.0,
        max_failures: int = 3,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_cooldown = base_cooldown
        self.lockout_duration = lockout_duration
        self.max_failures = max_failures
        self.time_func = time_func
        # user_id -> (last_attempt_timestamp, consecutive_failures)
        self._state: dict[str, tuple[float, int]] = {}

    def check(self, user_id: str) -> None:
        if user_id not in self._state:
            return
            
        last_time, failures = self._state[user_id]
        now = self.time_func()
        elapsed = now - last_time
        
        current_cooldown = self.lockout_duration if failures >= self.max_failures else self.base_cooldown
        
        if elapsed < current_cooldown:
            remaining = current_cooldown - elapsed
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Wait {remaining:.1f}s",
                headers={"Retry-After": str(max(1, int(round(remaining))))},
            )

    def record_attempt(self, user_id: str, is_correct: bool) -> None:
        now = self.time_func()
        failures = 0
        
        if user_id in self._state:
            _, old_failures = self._state[user_id]
            if not is_correct:
                failures = old_failures + 1
            else:
                failures = 0
        else:
            failures = 1 if not is_correct else 0
            
        self._state[user_id] = (now, failures)

        if len(self._state) > 1000:
            self._prune(now)

    def _prune(self, now: float) -> None:
        cutoff = now - max(self.base_cooldown, self.lockout_duration) * 2
        stale_keys = [k for k, (last_time, _) in self._state.items() if last_time < cutoff]
        for k in stale_keys:
            del self._state[k]

    def reset(self, user_id: Optional[str] = None) -> None:
        if user_id is not None:
            self._state.pop(user_id, None)
        else:
            self._state.clear()


_submit_limiter: Optional[KeySubmissionRateLimiter] = None

def get_submit_limiter() -> KeySubmissionRateLimiter:
    global _submit_limiter
    if _submit_limiter is None:
        _submit_limiter = KeySubmissionRateLimiter()
    return _submit_limiter
