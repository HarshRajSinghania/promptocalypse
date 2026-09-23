from fastapi import APIRouter
from app.models import RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(request: RegisterRequest) -> dict[str, str]:
    """
    Register a new participant or resume an existing user session.

    Validates username constraints (3-20 chars, alphanumeric/underscore/hyphen),
    creates a new user entry in the database or retrieves an existing one,
    and returns initial user state and session details.
    """
    return {
        "status": "not_implemented",
        "message": "TODO: Implement participant registration and session recovery",
    }
