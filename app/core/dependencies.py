"""Shared FastAPI dependencies – authentication helpers using Supabase."""

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.database import get_supabase
from app.crud.crud_user import user as crud_user

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Client = Depends(get_supabase),
) -> Dict[str, Any]:
    """Decode the Supabase JWT, fetch the user row from our public schema, mapping auth.users.id -> users.id."""
    token = credentials.credentials
    try:
        # 1. Verify Supabase JWT with Supabase Auth API
        auth_response = db.auth.get_user(token)
        if not auth_response or not auth_response.user:
            raise ValueError("User not found in Supabase Auth")
        
        user_id = auth_response.user.id
        auth_email = auth_response.user.email
        auth_metadata = auth_response.user.user_metadata or {}
        
        if not user_id:
            raise ValueError("Missing subject")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Get the user from our custom defined `users` table
    resp = (
        db.table("users")
        .select("*")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    user = resp.data

    if not user:
        if not auth_email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found and token has no email claim",
            )

        user = crud_user.ensure_profile(
            db,
            user_id=user_id,
            email=auth_email,
            username=auth_metadata.get("username"),
            display_name=auth_metadata.get("display_name"),
        )

    return user
