from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

connect_args = {}
if settings.database_url.startswith("postgresql"):
    connect_args = {"sslmode": "require"}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,        # tests connection before using it
    pool_recycle=300,           # recycle connections every 5 minutes
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()