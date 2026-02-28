"""Shared FastAPI dependencies – authentication helpers."""

from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.database import get_supabase
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Client = Depends(get_supabase),
) -> Dict[str, Any]:
    """Decode the JWT, fetch the user row from Supabase, raise 401 on failure."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise ValueError("Missing subject")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    resp = (
        db.table("users")
        .select("*")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    user = resp.data
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
