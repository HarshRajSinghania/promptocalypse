from fastapi import APIRouter, Query
from app.models import SubmitKeyRequest

router = APIRouter(prefix="/api", tags=["game"])


@router.post("/submit-key")
async def submit_key(request: SubmitKeyRequest) -> dict[str, str]:
    """
    Evaluate a submitted flag key for the participant's current level.

    Expected processing:
    1. Verify user exists and validate submitted key against level secret.
    2. Record submission attempt in submissions table.
    3. If correct on Levels 1-2: increment user level and unlock next level.
    4. If correct on Level 3: calculate final score, set completion timestamp.
    5. If incorrect: increment failed_attempts counter and deduct penalty points.
    """
    return {
        "status": "not_implemented",
        "message": "TODO: Implement key submission verification and level progression",
    }


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
