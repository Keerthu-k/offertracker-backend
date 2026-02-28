"""JWT token verification utilities for Supabase Auth."""

from typing import Any

import jwt

from app.core.config import settings

def verify_supabase_token(token: str) -> dict[str, Any]:
    """Decode and verify a Supabase Auth JWT using the project's JWT Secret."""
    try:
        # Supabase uses HS256 to sign tokens
        return jwt.decode(
            token, 
            settings.SUPABASE_JWT_SECRET, 
            algorithms=["HS256"],
            # Enable the 'aud' claim verification to ensure it's "authenticated"
            audience="authenticated"
        )
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")
