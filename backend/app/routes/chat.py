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
import httpx
import openai

from app.config import Settings, get_llm_config, get_settings
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
    """Dependency provider for AsyncOpenAI client with explicit timeout and provider base_url."""
    config = get_llm_config(settings)
    http_client = httpx.AsyncClient(timeout=8.0)
    return openai.AsyncOpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        http_client=http_client,
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
    1. Pre-flight log: Immediate trace before cooldown, validation, or inference.
    2. Cooldown check: Reject requests arriving within < 3.0s with HTTP 429.
    3. Session validation: Ensure participant exists and arena run is active.
    4. Update rate limit window: Mark request timestamp for the validated user.
    5. Level 2 Ingress Defense: Block prohibited keywords, short-circuit before Groq.
    6. LLM Inference: Dispatch context to Groq (llama-3.1-8b-instant).
    7. Level 3 Egress Defense: Mask secret key token leaks before dispatching reply.
    8. Persistence: Atomically record prompt interaction and update user metrics.
    """
    try:
        # Pre-flight log immediately at sentence 1 before redaction, DB access, or cooldown runs
        logger.info(
            "chat_endpoint_hit",
            extra={
                "event": "chat_endpoint_hit",
                "user_id": request.user_id,
                "prompt_len": len(request.prompt),
            },
            user_id=request.user_id,
            prompt_len=len(request.prompt),
        )

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

        # Step 2: Validate participant
        async with get_db_context() as db:
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
            async with get_db_context() as db:
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

        # Step 5: Dispatch LLM Inference call
        system_prompt = SYSTEM_PROMPTS.get(level, "")
        llm_cfg = get_llm_config(settings)
        active_model = llm_cfg["model"]
        logger.info(
            "Dispatching prompt to LLM provider",
            extra={
                "event": "llm_prompt_dispatched",
                "user_id": request.user_id,
                "challenge_level": level,
                "input_chars": len(request.prompt),
                "provider": llm_cfg["provider"],
                "model": active_model,
                "prompt": request.prompt,
            },
        )
        upstream_start = time.perf_counter()
        try:
            response = await client.chat.completions.create(
                model=active_model,
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
                    "provider": llm_cfg["provider"],
                    "model": active_model,
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
        async with get_db_context() as db:
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
                "provider": llm_cfg["provider"],
                "model": active_model,
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

    except HTTPException:
        # Re-raise intended HTTP exceptions (400, 404, 429, 502) without converting to 500
        raise
    except Exception as e:
        logger.exception("FATAL_CHAT_CRASH", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
