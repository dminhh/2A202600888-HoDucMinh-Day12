"""Rate Limiter — Sliding Window Counter algorithm."""
import time
from collections import defaultdict, deque
from fastapi import HTTPException

from app.config import settings

# key: api_key → deque của timestamps trong 60 giây
_windows: dict[str, deque] = defaultdict(deque)


def check_rate_limit(api_key: str) -> None:
    """
    Sliding Window: đếm số request trong 60 giây gần nhất.
    Vượt RATE_LIMIT_PER_MINUTE → 429 Too Many Requests.
    """
    now = time.time()
    window = _windows[api_key]

    # Loại bỏ timestamps cũ (ngoài window 60s)
    while window and window[0] < now - 60:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        retry_after = int(window[0] + 60 - now) + 1
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": 60,
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    window.append(now)
