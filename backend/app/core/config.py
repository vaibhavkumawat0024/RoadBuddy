from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "RoadBuddy AI"
    debug: bool = True

    # Database (PostgreSQL)
    database_url: str = "postgresql://user:password@localhost:5432/roadbuddy"

    # AI
    openai_api_key: str = ""
    gemini_api_key: str = ""

    # Google Maps
    google_maps_api_key: str = ""

    # JWT Auth
    secret_key: str = "change-this-to-a-long-random-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    class Config:
        env_file = ".env"


settings = Settings()
