"""Authentication endpoints – register & login via Supabase."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from app.core.database import get_supabase
from app.core.logging import logger
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
    try:
        # Check if username exists in public schema first before talking to Supabase Auth
        if crud_user.get_by_username(db, user_in.username):
            raise HTTPException(status_code=400, detail="Username already taken")

        if crud_user.get_by_email(db, user_in.email):
            raise HTTPException(status_code=400, detail="Email already taken")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Pre-registration check failed for %s: %s", user_in.email, exc)
        raise HTTPException(status_code=500, detail="Registration check failed")

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
        logger.error("Supabase Auth sign_up failed for %s: %s", user_in.email, e)
        raise HTTPException(status_code=400, detail=f"Registration failed: {e}")

    auth_user = auth_response.user
    if not auth_user:
        raise HTTPException(status_code=400, detail="Failed to create user with Supabase Auth.")

    user_id = auth_user.id

    # Ensure profile exists (trigger-first, API fallback if trigger not present yet).
    try:
        user_row = crud_user.ensure_profile(
            db,
            user_id=user_id,
            email=user_in.email,
            username=user_in.username,
            display_name=user_in.display_name,
        )
    except Exception as exc:
        logger.error("Failed to create user profile for %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to create user profile")

    # Award the "Getting Started" milestone
    try:
        getting_started = crud_milestone.get_by_field(
            db, field="name", value="Getting Started"
        )
        if getting_started:
            crud_user_milestone.award(db, user_row["id"], getting_started["id"])
    except Exception:
        pass  # Non-critical

    logger.info("User registered: %s (%s)", user_in.username, user_in.email)

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
    except Exception as exc:
        # Supabase raises exception for incorrect credentials
        logger.info("Login failed for %s: %s", credentials.email, exc)
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

    try:
        user_metadata = auth_response.user.user_metadata or {}
        user_row = crud_user.ensure_profile(
            db,
            user_id=user_id,
            email=auth_response.user.email or credentials.email,
            username=user_metadata.get("username"),
            display_name=user_metadata.get("display_name"),
        )
    except Exception as exc:
        logger.error("Failed to ensure profile on login for %s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load user profile")

    # Update streak on login (non-critical)
    try:
        crud_user.update_streak(db, user_row["id"])
    except Exception as exc:
        logger.warning("Streak update failed on login for %s: %s", user_id, exc)

    logger.info("User logged in: %s", credentials.email)

    return {
        "access_token": auth_response.session.access_token,
        "token_type": "bearer",
        "user": user_row
    }
