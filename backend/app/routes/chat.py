"""
Chat execution route with progressive defense security pipeline.

Implements Issue #2: [Security] Level 2 Ingress Regex Filter & Level 3 Egress Token Scrubber.
References:
- docs/FEATURES.md §2.2, §2.3, §2.4
- docs/TECH-SPEC.md §1.1, §2.2, §4
"""

import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
import openai

from app.config import Settings, get_settings
from app.database import get_db_context
from app.models import ChatRequest, ChatResponse
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
) -> ChatResponse:
    """
    Execute a user prompt against the target LLM for their current challenge level.

    Processing pipeline:
    1. Session validation: Ensure participant exists and arena run is active.
    2. Level 2 Ingress Defense: Block prohibited keywords, short-circuit before Groq.
    3. LLM Inference: Dispatch context to Groq (llama-3.1-8b-instant).
    4. Level 3 Egress Defense: Mask secret key token leaks before dispatching reply.
    5. Persistence: Atomically record prompt interaction and update user metrics.
    """
    async with get_db_context() as db:
        # Step 1: Validate participant
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

        # Step 2: Level 2 Ingress Defense (Short-circuit without calling Groq)
        if level == 2 and check_level2_ingress(request.prompt):
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
            return ChatResponse(
                reply=L2_FIREWALL_ALERT_REPLY,
                status="blocked",
                cooldown_seconds=settings.COOLDOWN_SECONDS,
            )

        # Step 3: Dispatch LLM Inference call to Groq
        system_prompt = SYSTEM_PROMPTS.get(level, "")
        start_time = time.perf_counter()
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
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Inference timeout or API error: {str(e)}",
            )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Step 4: Level 3 Egress Defense (Sanitize output tokens)
        if level == 3:
            reply, is_leak = scrub_level3_egress(raw_reply)
        else:
            reply, is_leak = raw_reply, False

        # Step 5: Ledger Persistence & Metrics
        await record_prompt_interaction(
            db=db,
            user_id=request.user_id,
            level=level,
            prompt_text=request.prompt,
            response_text=reply,
            char_count=len(request.prompt),
            latency_ms=latency_ms,
            is_firewall_blocked=False,
            is_leak_blocked=is_leak,
        )

        return ChatResponse(
            reply=reply,
            latency_ms=latency_ms,
            cooldown_seconds=settings.COOLDOWN_SECONDS,
        )
