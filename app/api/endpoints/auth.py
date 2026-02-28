"""Authentication endpoints – register & login."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.database import get_supabase
from app.core.security import hash_password, verify_password, create_access_token
from app.crud.crud_user import user as crud_user
from app.crud.crud_gamification import (
    milestone as crud_milestone,
    user_milestone as crud_user_milestone,
)
from app.schemas.user import UserRegister, UserLogin, TokenResponse

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    *,
    db: Client = Depends(get_supabase),
    user_in: UserRegister,
) -> Any:
    """Register a new user account."""
    if crud_user.get_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if crud_user.get_by_username(db, user_in.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    data = {
        "email": user_in.email,
        "username": user_in.username,
        "display_name": user_in.display_name or user_in.username,
        "password_hash": hash_password(user_in.password),
    }
    user_row = crud_user.create(db=db, data=data)

    # Award the "Getting Started" milestone
    getting_started = crud_milestone.get_by_field(
        db, field="name", value="Getting Started"
    )
    if getting_started:
        try:
            crud_user_milestone.award(db, user_row["id"], getting_started["id"])
        except Exception:
            pass  # Non-critical

    token = create_access_token(subject=user_row["id"])
    return {"access_token": token, "token_type": "bearer", "user": user_row}


@router.post("/login", response_model=TokenResponse)
def login(
    *,
    db: Client = Depends(get_supabase),
    credentials: UserLogin,
) -> Any:
    """Login with email and password."""
    user_row = crud_user.get_by_email(db, credentials.email)
    if not user_row or not verify_password(
        credentials.password, user_row["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(subject=user_row["id"])

    # Update streak on login
    crud_user.update_streak(db, user_row["id"])

    return {"access_token": token, "token_type": "bearer", "user": user_row}
