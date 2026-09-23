from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.game import router as game_router

app = FastAPI(title="AI Jailbreak Arena API")

# Add CORS middleware (allow all origins for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Startup event that initializes the database."""
    await init_db()


# Include all routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(game_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify backend availability."""
    return {"status": "ok"}
