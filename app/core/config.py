from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "OfferTracker API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Supabase configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""  # anon / service-role key

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
