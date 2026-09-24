import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.logger import logger, setup_logging
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.game import router as game_router
from app.routes.health import router as health_router

settings = get_settings()

app = FastAPI(title="AI Jailbreak Arena API")

# Configure CORS middleware
# Note: Wildcard origin "*" cannot be paired with allow_credentials=True per W3C CORS spec.
# Using explicit dev origins and allow_origin_regex dynamically mirrors the request origin.
cors_origins = [o for o in settings.CORS_ORIGINS if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    """
    HTTP timing and request metadata observability middleware.
    Attaches X-Process-Time header and logs structured request metrics.
    """
    start_time = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        content_length = request.headers.get("content-length")
        char_length = int(content_length) if content_length and content_length.isdigit() else 0

        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request",
                "method": request.method,
                "endpoint": request.url.path,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "char_length": char_length,
                "status_code": response.status_code,
                "latency_ms": round(duration_ms, 2),
            },
        )
        return response
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "HTTP request unhandled exception",
            extra={
                "event": "http_request_error",
                "method": request.method,
                "endpoint": request.url.path,
                "ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
                "status_code": 500,
                "latency_ms": round(duration_ms, 2),
                "error": str(exc),
            },
            exc_info=True,
        )
        raise exc


@app.on_event("startup")
async def startup_event() -> None:
    """Startup event that initializes logging and database."""
    setup_logging(log_file_path=settings.LOG_FILE_PATH)
    await init_db()


# Include all routers
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(game_router)
app.include_router(health_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint to verify backend availability."""
    return {"status": "ok"}

