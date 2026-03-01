from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "OfferTracker API"
    VERSION: str = "0.4.0"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: str = "*"  # Comma-separated list of origins, e.g. "http://localhost:5173,https://myfrontend.com"

    # Supabase configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # anon key (public)
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # service role key (server-side only, keep secret)
    
    # Supabase JWT secret – found in Supabase Dashboard → Settings → API → JWT Secret
    # Used to verify tokens issued by Supabase Auth
    SUPABASE_JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
