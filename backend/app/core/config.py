from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RoadBuddy AI"
    debug: bool = False

    # Database (PostgreSQL)
    database_url: str

    # AI
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    duffel_api_key: str = ""

    # Google Maps / Routing
    open_router_service_api_key: str = ""

    # Resend API (Email)
    resend_api_key: str = ""

    # Brevo API (Email) -- works without domain verification, unlike Resend sandbox
    brevo_api_key: str = ""
    brevo_sender_email: str = "kunalsinghtanwar355@gmail.com"

    # Razorpay Payment Gateway API
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # Mapbox API
    mapbox_access_token: str = ""

    # JWT Auth
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    allowed_origins: list[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8081",
        "http://127.0.0.1:8081"
    ]

    # Fuel station availability feature
    demo_mode: bool = False               # Set DEMO_MODE=true in .env to enable debug/simulate-time endpoint
    operator_decay_hours: float = 4.0     # Hours for operator-confirmed confidence to decay to 0%
    crowdsource_decay_hours: float = 1.5  # Hours for crowdsourced confidence to decay to 0%

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()