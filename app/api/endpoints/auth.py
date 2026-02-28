"""Authentication endpoints – register & login via Supabase."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.core.database import get_supabase
from app.crud.crud_user import user as crud_user
from app.crud.crud_gamification import (
    milestone as crud_milestone,
    user_milestone as crud_user_milestone,
)
from app.schemas.user import UserRegister, UserLogin

router = APIRouter()

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    *,
    db: Client = Depends(get_supabase),
    user_in: UserRegister,
) -> Any:
    """Register a new user account via Supabase Auth."""
    # Check if username exists in public schema first before talking to Supabase Auth
    if crud_user.get_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    if crud_user.get_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already taken")

    # 1. Sign up user via Supabase Auth
    try:
        auth_response = db.auth.sign_up(
            {
                "email": user_in.email,
                "password": user_in.password,
                "options": {
                    "data": {
                        "username": user_in.username,
                        "display_name": user_in.display_name or user_in.username,
                    }
                },
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    auth_user = auth_response.user
    if not auth_user:
        raise HTTPException(status_code=400, detail="Failed to create user with Supabase Auth.")

    user_id = auth_user.id

    # Ensure profile exists (trigger-first, API fallback if trigger not present yet).
    user_row = crud_user.ensure_profile(
        db,
        user_id=user_id,
        email=user_in.email,
        username=user_in.username,
        display_name=user_in.display_name,
    )

    # Award the "Getting Started" milestone
    getting_started = crud_milestone.get_by_field(
        db, field="name", value="Getting Started"
    )
    if getting_started:
        try:
            crud_user_milestone.award(db, user_row["id"], getting_started["id"])
        except Exception:
            pass  # Non-critical

    return {
        "access_token": auth_response.session.access_token if auth_response.session else "",
        "token_type": "bearer",
        "user": user_row
    }


@router.post("/login", response_model=TokenResponse)
def login(
    *,
    db: Client = Depends(get_supabase),
    credentials: UserLogin,
) -> Any:
    """Login with email and password via Supabase Auth."""
    try:
        auth_response = db.auth.sign_in_with_password(
            {
                "email": credentials.email,
                "password": credentials.password,
            }
        )
    except Exception:
        # Supabase raises exception for incorrect credentials
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not auth_response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session could not be established",
        )

    user_id = auth_response.user.id

    user_metadata = auth_response.user.user_metadata or {}
    user_row = crud_user.ensure_profile(
        db,
        user_id=user_id,
        email=auth_response.user.email or credentials.email,
        username=user_metadata.get("username"),
        display_name=user_metadata.get("display_name"),
    )

    # Update streak on login
    crud_user.update_streak(db, user_row["id"])

    return {
        "access_token": auth_response.session.access_token,
        "token_type": "bearer",
        "user": user_row
    }
