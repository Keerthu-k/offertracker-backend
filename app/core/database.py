import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
# Use anon key for standard operations
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)

# Admin client with service-role key, useful for bypassing Row Level Security
# if we really need it on backend, or specifically to administer users
service_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
supabase_admin: Client = create_client(url, service_key) if service_key else None


def get_supabase() -> Client:
    """Return the Supabase anon client instance (used as a FastAPI dependency)."""
    return supabase

def get_supabase_admin() -> Client:
    """Return the Supabase admin client instance with service roles"""
    if not supabase_admin:
        raise ValueError("Service role key is not configured.")
    return supabase_admin
