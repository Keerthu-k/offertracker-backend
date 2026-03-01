"""User profile endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.crud.crud_base import DatabaseError
from app.crud.crud_user import user as crud_user
from app.schemas.user import UserResponse, UserUpdate, UserPublicProfile

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get the currently authenticated user."""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    *,
    db: Client = Depends(get_supabase),
    current_user: Dict[str, Any] = Depends(get_current_user),
    user_in: UserUpdate,
) -> Any:
    """Update current user's profile."""
    try:
        update_data = user_in.model_dump(exclude_unset=True)
        return crud_user.update(db=db, id=current_user["id"], data=update_data)
    except DatabaseError as exc:
        logger.error("Failed to update user profile %s: %s", current_user["id"], exc)
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.get("/search", response_model=List[UserPublicProfile])
def search_users(
    *,
    db: Client = Depends(get_supabase),
    q: str = "",
    skip: int = 0,
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Search public user profiles by username or display name."""
    if not q:
        return []
    try:
        return crud_user.search_users(db, query=q, skip=skip, limit=limit)
    except Exception as exc:
        logger.error("User search failed (q=%s): %s", q, exc)
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/{user_id}", response_model=UserPublicProfile)
def get_user_profile(
    *,
    db: Client = Depends(get_supabase),
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get a user's public profile."""
    try:
        user_row = crud_user.get(db, id=user_id)
    except DatabaseError as exc:
        logger.error("Failed to fetch user profile %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to fetch user profile")

    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    # Allow viewing own profile even if private
    profile_visibility = user_row.get("profile_visibility", "private")
    is_public = user_row.get("is_profile_public", False) or profile_visibility == "public"
    if user_id != current_user["id"] and not is_public:
        raise HTTPException(status_code=403, detail="Profile is private")
    return user_row
