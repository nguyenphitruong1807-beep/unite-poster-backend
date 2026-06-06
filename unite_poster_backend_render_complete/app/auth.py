from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, status

from .config import get_settings
from .supabase_client import assert_admin_client, fetch_profile_by_user_id


async def get_current_user_optional(authorization: str | None = Header(default=None)) -> Optional[dict[str, Any]]:
    settings = get_settings()
    if not authorization:
        if settings.REQUIRE_AUTH_FOR_MUTATIONS:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu Bearer token")
        return None

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization phải có dạng Bearer <token>")

    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu access token")

    try:
        client = assert_admin_client()
        auth_response = client.auth.get_user(token)
        user = getattr(auth_response, "user", None)
        if user is None and isinstance(auth_response, dict):
            user = auth_response.get("user")
        if user is None:
            raise ValueError("Không xác thực được token")

        user_id = getattr(user, "id", None) or user.get("id")
        user_email = getattr(user, "email", None) or user.get("email")
        profile = fetch_profile_by_user_id(user_id) or {}
        return {
            "id": user_id,
            "email": user_email,
            "role": profile.get("role"),
            "full_name": profile.get("full_name"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token không hợp lệ: {exc}") from exc


async def require_authenticated_user(user: Optional[dict[str, Any]] = Depends(get_current_user_optional)) -> dict[str, Any]:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cần đăng nhập để dùng API này")
    return user


async def require_admin(user: dict[str, Any] = Depends(require_authenticated_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cần quyền admin")
    return user
