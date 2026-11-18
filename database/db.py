from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config.settings import DATABASE_URL

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

def create_test_session(database_url: str):
    """Create an isolated engine/session factory for tests or local experiments."""
    test_engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    return test_engine, sessionmaker(bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False)()

def init_db() -> None:
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # Safe additive migration for databases created before owner authentication.
    columns = {column["name"] for column in inspect(engine).get_columns("properties")}
    if "owner_id" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE properties ADD COLUMN owner_id INTEGER REFERENCES owners(id)"))

def get_session():
    return SessionLocal()
