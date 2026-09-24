"""
Chat execution route with progressive defense security pipeline and rate limiting.

Implements:
- Issue #2: [Security] Level 2 Ingress Regex Filter & Level 3 Egress Token Scrubber
- Issue #3: [Backend] Sliding-Window 3-Second Rate Limiter
References:
- docs/PRD.md §4, §6
- docs/FEATURES.md §2.1, §2.2, §2.3, §2.4
- docs/TECH-SPEC.md §1.1, §2.2, §4
- docs/SAD.md §2.2
"""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
import openai

from app.config import Settings, get_settings
from app.database import get_db_context
from app.logger import logger
from app.models import ChatRequest, ChatResponse
from app.rate_limiter import SlidingWindowRateLimiter, get_rate_limiter
from app.security import (
    L2_FIREWALL_ALERT_REPLY,
    L2_FIREWALL_INTERCEPT_TEXT,
    SYSTEM_PROMPTS,
    check_level2_ingress,
    record_prompt_interaction,
    scrub_level3_egress,
)

router = APIRouter(prefix="/api", tags=["chat"])


def get_groq_client(
    settings: Annotated[Settings, Depends(get_settings)]
) -> openai.AsyncOpenAI:
    """Dependency provider for Groq AsyncOpenAI client."""
    return openai.AsyncOpenAI(
        base_url=settings.GROQ_BASE_URL,
        api_key=settings.GROQ_API_KEY,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    client: Annotated[openai.AsyncOpenAI, Depends(get_groq_client)],
    limiter: Annotated[SlidingWindowRateLimiter, Depends(get_rate_limiter)],
) -> ChatResponse:
    """
    Execute a user prompt against the target LLM for their current challenge level.

    Processing pipeline:
    1. Cooldown check: Reject requests arriving within < 3.0s with HTTP 429.
    2. Session validation: Ensure participant exists and arena run is active.
    3. Update rate limit window: Mark request timestamp for the validated user.
    4. Level 2 Ingress Defense: Block prohibited keywords, short-circuit before Groq.
    5. LLM Inference: Dispatch context to Groq (llama-3.1-8b-instant).
    6. Level 3 Egress Defense: Mask secret key token leaks before dispatching reply.
    7. Persistence: Atomically record prompt interaction and update user metrics.
    """
    # Start total processing timer
    total_start = time.perf_counter()

    # Step 1: Cooldown check (Sliding-window rate limiter)
    try:
        limiter.check(request.user_id)
    except HTTPException as e:
        logger.warning(
            "Rate limit cooldown active for user",
            extra={
                "event": "rate_limit_exceeded",
                "user_id": request.user_id,
                "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                "detail": e.detail,
            },
        )
        raise

    async with get_db_context() as db:
        # Step 2: Validate participant
        cursor = await db.execute(
            "SELECT current_level, completed_at FROM users WHERE id = ?",
            (request.user_id,),
        )
        user_row = await cursor.fetchone()
        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        if user_row["completed_at"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arena already completed!",
            )

        level = user_row["current_level"]

        # Step 3: Record accepted request timestamp for rate limiter
        limiter.update(request.user_id)

        # Step 4: Level 2 Ingress Defense (Short-circuit without calling Groq)
        if level == 2 and check_level2_ingress(request.prompt):
            total_latency_ms = int((time.perf_counter() - total_start) * 1000)
            await record_prompt_interaction(
                db=db,
                user_id=request.user_id,
                level=level,
                prompt_text=request.prompt,
                response_text=L2_FIREWALL_INTERCEPT_TEXT,
                char_count=len(request.prompt),
                latency_ms=0,
                is_firewall_blocked=True,
                is_leak_blocked=False,
            )
            logger.info(
                "Ingress firewall intercepted prohibited prompt",
                extra={
                    "event": "ingress_firewall_blocked",
                    "user_id": request.user_id,
                    "challenge_level": level,
                    "input_chars": len(request.prompt),
                    "output_chars": len(L2_FIREWALL_ALERT_REPLY),
                    "guardrail_status": "firewall_blocked",
                    "is_firewall_blocked": True,
                    "is_leak_blocked": False,
                    "upstream_latency_ms": 0,
                    "total_latency_ms": total_latency_ms,
                    "provider": settings.GROQ_MODEL,
                    "status_code": status.HTTP_200_OK,
                    "prompt": request.prompt,
                },
            )
            return ChatResponse(
                reply=L2_FIREWALL_ALERT_REPLY,
                status="blocked",
                cooldown_seconds=settings.COOLDOWN_SECONDS,
            )

        # Step 5: Dispatch LLM Inference call to Groq
        system_prompt = SYSTEM_PROMPTS.get(level, "")
        logger.info(
            "Dispatching prompt to LLM provider",
            extra={
                "event": "llm_prompt_dispatched",
                "user_id": request.user_id,
                "challenge_level": level,
                "input_chars": len(request.prompt),
                "provider": settings.GROQ_MODEL,
                "prompt": request.prompt,
            },
        )
        upstream_start = time.perf_counter()
        try:
            response = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.prompt},
                ],
                temperature=0.2,
                max_tokens=settings.MAX_TOKENS,
                timeout=8.0,
            )
            raw_reply = response.choices[0].message.content or ""
        except Exception as e:
            # Upstream error/timeout: user prompt count is NOT penalized
            limiter.reset(request.user_id)
            upstream_latency_ms = int((time.perf_counter() - upstream_start) * 1000)
            total_latency_ms = int((time.perf_counter() - total_start) * 1000)
            logger.error(
                "Upstream LLM inference failure or timeout",
                extra={
                    "event": "llm_completion_failed",
                    "user_id": request.user_id,
                    "challenge_level": level,
                    "input_chars": len(request.prompt),
                    "upstream_latency_ms": upstream_latency_ms,
                    "total_latency_ms": total_latency_ms,
                    "provider": settings.GROQ_MODEL,
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                    "error": str(e),
                    "prompt": request.prompt,
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Inference timeout or API error: {str(e)}",
            )

        upstream_latency_ms = int((time.perf_counter() - upstream_start) * 1000)

        # Step 6: Level 3 Egress Defense (Sanitize output tokens)
        if level == 3:
            reply, is_leak = scrub_level3_egress(raw_reply)
        else:
            reply, is_leak = raw_reply, False

        # Step 7: Ledger Persistence & Metrics
        await record_prompt_interaction(
            db=db,
            user_id=request.user_id,
            level=level,
            prompt_text=request.prompt,
            response_text=reply,
            char_count=len(request.prompt),
            latency_ms=upstream_latency_ms,
            is_firewall_blocked=False,
            is_leak_blocked=is_leak,
        )

        total_latency_ms = int((time.perf_counter() - total_start) * 1000)

        token_usage: dict[str, int] = {}
        if hasattr(response, "usage") and response.usage:
            token_usage = {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                "total_tokens": getattr(response.usage, "total_tokens", 0),
            }

        logger.info(
            "LLM completion success",
            extra={
                "event": "llm_completion_success",
                "user_id": request.user_id,
                "challenge_level": level,
                "input_chars": len(request.prompt),
                "output_chars": len(reply),
                "guardrail_status": "leak_masked" if is_leak else "clean",
                "is_firewall_blocked": False,
                "is_leak_blocked": is_leak,
                "upstream_latency_ms": upstream_latency_ms,
                "total_latency_ms": total_latency_ms,
                "provider": settings.GROQ_MODEL,
                "status_code": status.HTTP_200_OK,
                "prompt": request.prompt,
                "token_usage": token_usage,
            },
        )

        return ChatResponse(
            reply=reply,
            latency_ms=upstream_latency_ms,
            cooldown_seconds=settings.COOLDOWN_SECONDS,
        )
