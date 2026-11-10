from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import database_url

_url = database_url()
engine = create_engine(
    _url, connect_args={"check_same_thread": False} if _url.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
