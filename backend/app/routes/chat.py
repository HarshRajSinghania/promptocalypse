from fastapi import APIRouter
from app.models import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    """
    Execute a user prompt against the target LLM for their current challenge level.

    Expected processing pipeline:
    1. Cooldown check: Enforce hard 3-second cooldown per user.
    2. Ingress filter: Level 2 regex/keyword filtering on user prompt.
    3. Groq call: Dispatch system prompt + conversation context to Groq API.
    4. Egress filter: Level 3 leak masking to prevent accidental flag leakage.
    5. Ledger write: Log prompt, response, metrics, and flags in prompt_ledger.
    """
    return {
        "status": "not_implemented",
        "message": "TODO: Implement chat execution pipeline (cooldown check, L2 ingress filter, Groq call, L3 egress filter, ledger write)",
    }
