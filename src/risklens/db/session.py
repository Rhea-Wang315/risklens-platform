"""Database session management."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from risklens.config import get_settings

settings = get_settings()

# Create engine with connection pooling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=False,  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, Any, None]:
    """Get database session.
    
    Usage:
        from risklens.db.session import get_db
        
        with next(get_db()) as db:
            db.query(DecisionRecord).all()
    
    Or with FastAPI dependency injection:
        @app.get("/decisions")
        def get_decisions(db: Session = Depends(get_db)):
            return db.query(DecisionRecord).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database (create all tables).
    
    Note: In production, use Alembic migrations instead.
    This is only for testing and development.
    """
    from risklens.db.models import Base

    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables.
    
    WARNING: This will delete all data!
    Only use in testing.
    """
    from risklens.db.models import Base

    Base.metadata.drop_all(bind=engine)
