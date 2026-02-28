"""User profile endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user
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
    update_data = user_in.model_dump(exclude_unset=True)
    return crud_user.update(db=db, id=current_user["id"], data=update_data)


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
    return crud_user.search_users(db, query=q, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserPublicProfile)
def get_user_profile(
    *,
    db: Client = Depends(get_supabase),
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Any:
    """Get a user's public profile."""
    user_row = crud_user.get(db, id=user_id)
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    # Allow viewing own profile even if private
    if user_id != current_user["id"] and not user_row.get("is_profile_public", False):
        raise HTTPException(status_code=403, detail="Profile is private")
    return user_row
