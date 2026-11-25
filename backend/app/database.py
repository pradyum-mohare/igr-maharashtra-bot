from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_schema_columns():
    """Apply additive column migrations safely for existing databases."""
    statements = [
        "ALTER TABLE search_jobs ADD COLUMN IF NOT EXISTS captcha_refresh_requested BOOLEAN DEFAULT FALSE",
        "ALTER TABLE search_jobs ADD COLUMN IF NOT EXISTS cancel_requested BOOLEAN DEFAULT FALSE",
        "ALTER TABLE search_jobs ADD COLUMN IF NOT EXISTS portal_notice TEXT",
        "ALTER TABLE property_records ADD COLUMN IF NOT EXISTS district VARCHAR(150)",
        "ALTER TABLE property_records ADD COLUMN IF NOT EXISTS tahsil_or_village VARCHAR(255)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
