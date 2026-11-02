from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from app.core.config import get_settings

settings = get_settings()

# Global engine and session factory - can be reset for testing
_engine = None
_SessionLocal = None


def _create_engine_and_session(url: str):
    """Create engine and session factory."""
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        pool_pre_ping=True,
        echo=settings.debug,
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, session_factory


def get_engine():
    """Get or create the database engine."""
    global _engine, _SessionLocal
    if _engine is None:
        _engine, _SessionLocal = _create_engine_and_session(settings.database_url)
    return _engine


def get_session_local():
    """Get or create the session factory."""
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine, _SessionLocal = _create_engine_and_session(settings.database_url)
    return _SessionLocal


def reset_engine_for_test(url: str = "sqlite:///:memory:") -> None:
    """Reset engine for testing. Call before running tests."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine, _SessionLocal = _create_engine_and_session(url)


def init_db() -> None:
    """Create all tables. Call on startup."""
    from app.models import Base
    Base.metadata.create_all(bind=get_engine())


class Base(DeclarativeBase):
    pass


# Provide engine and SessionLocal as properties for backward compatibility
# These will lazily initialize on first access
class _EngineProxy:
    def __getattr__(self, name):
        return getattr(get_engine(), name)


class _SessionLocalProxy:
    def __call__(self, *args, **kwargs):
        return get_session_local()(*args, **kwargs)
    
    def __getattr__(self, name):
        return getattr(get_session_local(), name)


engine = _EngineProxy()
SessionLocal = _SessionLocalProxy()


def get_db() -> Generator[Session, None, None]:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions outside of FastAPI dependencies."""
    db = get_session_local()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
