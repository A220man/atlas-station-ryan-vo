import pytest
import os

# Set test database URL before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.core.database import Base, get_db, reset_engine_for_test, get_engine
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_engine():
    reset_engine_for_test("sqlite:///./test.db")
    from app.models import Base
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after all tests
    engine.dispose()
    # Clean up test database file
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test using the test engine."""
    from app.core.database import get_session_local
    from app.models import Job, VideoFile, JobEvent
    
    SessionLocal = get_session_local()
    session = SessionLocal()
    # Clean up any existing data
    session.query(JobEvent).delete()
    session.query(VideoFile).delete()
    session.query(Job).delete()
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden database dependency."""
    from fastapi.testclient import TestClient
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
