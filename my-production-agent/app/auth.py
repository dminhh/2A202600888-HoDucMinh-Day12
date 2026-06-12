"""API Key Authentication."""
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Kiểm tra X-API-Key header.
    - Không có key → 401 Unauthorized
    - Sai key → 401 Unauthorized
    - Đúng key → trả về api_key (dùng làm user identifier)
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include header: X-API-Key: <your-key>",
        )
    if api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )
    return api_key
