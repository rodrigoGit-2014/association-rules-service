"""Database session management with SQLAlchemy"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """Dependency function to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables defined in models, and add missing columns"""
    from app.db.base import Base
    from sqlalchemy import text, inspect
    import logging

    logger = logging.getLogger(__name__)

    Base.metadata.create_all(bind=engine)

    # Add missing columns to existing tables
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name not in existing_columns:
                    col_type = column.type.compile(dialect=engine.dialect)
                    nullable = "NULL" if column.nullable else "NOT NULL"
                    default_clause = ""
                    if column.server_default is not None:
                        default_val = column.server_default.arg.text if hasattr(column.server_default.arg, 'text') else str(column.server_default.arg)
                        default_clause = f" DEFAULT '{default_val}'"
                    sql = f'ALTER TABLE {table_name} ADD COLUMN "{column.name}" {col_type}{default_clause} {nullable}'
                    logger.info(f"Adding missing column: {sql}")
                    conn.execute(text(sql))
