"""
Game progression routes: flag submission verification.

Implements Issue #4: Scoring Engine.
References:
- docs/TECH-SPEC.md §2.3 (Challenge Progression), §5 (Scoring & State Machine)
- docs/FEATURES.md Phase 3 (Vault Validation, Scoring & Progression)
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.database import get_db_context
from app.models import SubmitKeyRequest, SubmitKeyResponse
from app.scoring import (
    STATUS_ALREADY_COMPLETED,
    STATUS_COMPLETED,
    STATUS_CORRECT,
    STATUS_INCORRECT,
    STATUS_NOT_FOUND,
    verify_and_progress,
)

router = APIRouter(prefix="/api", tags=["game"])


@router.post("/submit-key", response_model=SubmitKeyResponse)
async def submit_key(request: SubmitKeyRequest) -> SubmitKeyResponse:
    """
    Evaluate a submitted flag key for the participant's current level.

    Processing pipeline (atomic, TECH-SPEC.md §5.2):
    1. Verify user exists and validate submitted key against the level secret
       using a constant-time comparison (hmac.compare_digest).
    2. Record every submission attempt in the submissions table.
    3. If correct on Levels 1-2: increment user level and unlock next level.
    4. If correct on Level 3: calculate final score, set completion timestamp.
    5. If incorrect: increment failed_attempts counter (25 pt penalty).
    """
    async with get_db_context() as db:
        result = await verify_and_progress(
            db=db, user_id=request.user_id, submitted_key=request.key
        )

    outcome = result["status"]

    if outcome == STATUS_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if outcome == STATUS_ALREADY_COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arena already completed!",
        )

    if outcome == STATUS_INCORRECT:
        return SubmitKeyResponse(
            status=STATUS_INCORRECT,
            unlocked_level=result["unlocked_level"],
            penalty_points=result["penalty_points"],
            message=result["message"],
        )

    if outcome == STATUS_CORRECT:
        return SubmitKeyResponse(
            status=STATUS_CORRECT,
            unlocked_level=result["unlocked_level"],
            message=result["message"],
        )

    # STATUS_COMPLETED
    return SubmitKeyResponse(
        status=STATUS_COMPLETED,
        message=result["message"],
        final_score=result["final_score"],
        completion_time=result["completion_time"],
        stats=result["stats"],
    )


@router.get("/leaderboard")
async def get_leaderboard() -> dict[str, str]:
    """
    Retrieve ranked leaderboard of participants.

    Expected processing:
    Query users table ordered by final_score (DESC), current_level (DESC),
    total_prompts (ASC), total_chars (ASC), and completion time.
    """
    return {
        "status": "not_implemented",
        "message": "TODO: Implement leaderboard ranking retrieval",
    }


@router.get("/user/state")
async def get_user_state(
    user_id: str = Query(..., description="Unique participant ID")
) -> dict[str, str]:
    """
    Retrieve current game state and telemetry for a participant.

    Expected processing:
    Query user metrics, current level, elapsed time, prompt count, and completion status.
    """
    return {
        "status": "not_implemented",
        "message": "TODO: Implement user state and telemetry retrieval",
    }
