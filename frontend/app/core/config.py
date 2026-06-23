import os

# Backend API base URL. Override with BACKEND_URL env var in production.
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# Cookie used to store the JWT issued by the backend after login.
AUTH_COOKIE_NAME = "roadbuddy_token"

# Set to True in production (requires HTTPS).
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
