import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.core.auth import hash_password, create_access_token
from app.models.models import User

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite:///./test.db",
)

connect_args = {}
if TEST_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(TEST_DATABASE_URL, connect_args=connect_args)

from app.models import models
Base.metadata.create_all(bind=engine)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_tables():
    """Drop and recreate all tables between tests for full isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Also clear the in-memory OTP store to avoid rate-limit bleed
    from app.core.email_otp import _otp_store
    _otp_store.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    """Provide a raw DB session for tests that need direct model access."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_test_user(
    email: str = "test@roadbuddy.com",
    password: str = "Test123",
    name: str = "Test User",
) -> dict:
    """
    Insert a user directly into the DB (bypassing OTP email flow)
    and return {"user": User, "token": str}.
    """
    db = TestingSessionLocal()
    try:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_access_token({"sub": str(user.id)})
        return {"user": user, "token": token}
    finally:
        db.close()