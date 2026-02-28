import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)


def get_supabase() -> Client:
    """Return the Supabase client instance (used as a FastAPI dependency)."""
    return supabase
