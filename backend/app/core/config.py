from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "RoadBuddy AI"
    debug: bool = False

    # Database (PostgreSQL)
    database_url: str

    # AI
    openai_api_key: str = ""
    groq_api_key: str = ""

    # Google Mapsgit a
    open_router_service_api_key: str = ""

    # JWT Auth
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_server: str = "smtp.gmail.com"
    mail_port: int = 587

    allowed_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    class Config:
        env_file = ".env"


settings = Settings()
