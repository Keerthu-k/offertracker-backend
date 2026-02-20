from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "OfferTracker API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Postgres configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "offertracker"
    POSTGRES_PORT: str = "5432"

    @property
    def async_database_uri(self) -> str:
        return "sqlite+aiosqlite:///./offertracker.db"
    
    @property
    def sync_database_uri(self) -> str:
        return "sqlite:///./offertracker.db"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
