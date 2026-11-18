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
    _migrate_notification_event_key()
    # Safe additive migration for databases created before owner authentication.
    columns = {column["name"] for column in inspect(engine).get_columns("properties")}
    if "owner_id" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE properties ADD COLUMN owner_id INTEGER REFERENCES owners(id)"))

def get_session():
    return SessionLocal()


def _migrate_notification_event_key() -> None:
    """Safely replace the old notification uniqueness constraint.

    Older databases had one unique row per tenant/rent/type. The event key is
    required to preserve sent history while allowing a later distinct event.
    Existing rows are copied with stable legacy keys; no operational data is
    discarded.
    """
    inspector = inspect(engine)
    if "notification_logs" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("notification_logs")}
    if "event_key" in columns:
        return
    notification_table = Base.metadata.tables["notification_logs"]
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("ALTER TABLE notification_logs RENAME TO notification_logs_legacy")
        legacy_indexes = connection.exec_driver_sql("PRAGMA index_list('notification_logs_legacy')").fetchall()
        for index in legacy_indexes:
            index_name = index[1]
            if not index_name.startswith("sqlite_autoindex"):
                connection.exec_driver_sql(f'DROP INDEX IF EXISTS "{index_name}"')
        notification_table.create(connection, checkfirst=True)
        connection.execute(text("""
            INSERT INTO notification_logs
                (id, tenant_id, rent_record_id, notification_type, event_key,
                 recipient, message, scheduled_at, sent_at, delivery_status, created_at)
            SELECT id, tenant_id, rent_record_id, notification_type,
                   'legacy-' || id, recipient, message, scheduled_at, sent_at,
                   delivery_status, created_at
            FROM notification_logs_legacy
        """))
        connection.exec_driver_sql("DROP TABLE notification_logs_legacy")
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
