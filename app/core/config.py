from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "OfferTracker API"
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"

    # Supabase configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # anon / service-role key

    # JWT configuration
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
