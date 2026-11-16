"""
Database engine and session setup using SQLAlchemy.
Backend developer should use `get_db()` dependency in FastAPI routes.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and ensure schema migrations. Call once at startup."""
    import backend.models  # noqa: F401  — ensure models are registered
    Base.metadata.create_all(bind=engine)

    # Lightweight schema migration for SQLite
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # Check existing columns on meetings table
            res = conn.execute(text("PRAGMA table_info(meetings)")).fetchall()
            existing_cols = {row[1] for row in res}
            cols_to_add = [
                ("attendees_json", "TEXT DEFAULT '[]'"),
                ("meet_link", "VARCHAR(500)"),
                ("calendar_event_id", "VARCHAR(200)"),
                ("status", "VARCHAR(20) DEFAULT 'scheduled'"),
                ("notification_status", "TEXT DEFAULT ''"),
            ]
            for col_name, col_type in cols_to_add:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE meetings ADD COLUMN {col_name} {col_type}"))
            conn.commit()
    except Exception as e:
        print("Schema migration check error:", e)
