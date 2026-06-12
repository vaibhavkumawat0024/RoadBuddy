import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db

# Use Neon DB for tests with SSL
TEST_DATABASE_URL = "postgresql://neondb_owner:npg_rbiTAUDG9I7w@ep-plain-truth-afcr7ttp.c-2.us-west-2.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"sslmode": "require"}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)