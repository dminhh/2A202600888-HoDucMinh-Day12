"""Cost Guard — Bảo vệ budget LLM theo tháng."""
import time
from fastapi import HTTPException

from app.config import settings

# key: "{api_key}:{YYYY-MM}" → cost (USD)
_spending: dict[str, float] = {}

PRICE_PER_1K_INPUT_TOKENS = 0.00015   # $0.15/1M input
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006   # $0.60/1M output


def _month_key(api_key: str) -> str:
    month = time.strftime("%Y-%m")
    return f"{api_key}:{month}"


def check_budget(api_key: str) -> None:
    """
    Kiểm tra budget tháng của user.
    Vượt MONTHLY_BUDGET_USD → 402 Payment Required.
    """
    key = _month_key(api_key)
    spent = _spending.get(key, 0.0)

    if spent >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "spent_usd": round(spent, 4),
                "budget_usd": settings.monthly_budget_usd,
                "resets_at": "1st of next month",
            },
        )


def record_usage(api_key: str, input_tokens: int, output_tokens: int) -> float:
    """Ghi nhận cost sau khi gọi LLM xong."""
    key = _month_key(api_key)
    cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS + \
           (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    _spending[key] = _spending.get(key, 0.0) + cost
    return _spending[key]
