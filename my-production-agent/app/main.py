"""
Production AI Agent — kết hợp tất cả Day 12 concepts:
  - Config từ env vars
  - API Key authentication
  - Rate limiting
  - Cost guard
  - Health + Readiness check
  - Graceful shutdown
  - JSON logging
"""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget

# Mock LLM
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils.mock_llm import ask as llm_ask

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_in_flight = 0

# ─────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({"event": "startup", "app": settings.app_name}))
    time.sleep(0.1)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    # Chờ in-flight requests hoàn thành (tối đa 30s)
    timeout, elapsed = 30, 0
    while _in_flight > 0 and elapsed < timeout:
        time.sleep(1)
        elapsed += 1
    logger.info(json.dumps({"event": "shutdown"}))


# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.middleware("http")
async def track_requests(request: Request, call_next):
    global _in_flight
    _in_flight += 1
    start = time.time()
    try:
        response = await call_next(request)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round((time.time() - start) * 1000, 1),
        }))
        return response
    finally:
        _in_flight -= 1


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.post("/ask", response_model=AskResponse)
async def ask_agent(
    body: AskRequest,
    api_key: str = Depends(verify_api_key),
):
    check_rate_limit(api_key)
    check_budget(api_key)

    logger.info(json.dumps({"event": "agent_call", "q_len": len(body.question)}))
    answer = llm_ask(body.question)

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health")
def health():
    """Liveness probe — platform restart nếu non-200."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    """Readiness probe — load balancer không route vào nếu 503."""
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Not ready yet")
    return {"ready": True, "in_flight": _in_flight}


# ─────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────
def handle_sigterm(signum, frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, handle_sigterm)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
