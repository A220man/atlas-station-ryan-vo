import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, SessionLocal, get_db, init_db
from app.models import Job, VideoFile, JobStatus, JobType
from app.api.schemas import VideoFileStatus


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestModels:
    def test_job_creation(self, db_session):
        job = Job(
            type=JobType.RESTORATION,
            status=JobStatus.PENDING,
        )
        db_session.add(job)
        db_session.commit()
        
        assert job.id is not None
        assert job.type == JobType.RESTORATION
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
        assert job.created_at is not None

    def test_job_status_transitions(self, db_session):
        job = Job(type=JobType.RESTORATION, status=JobStatus.PENDING)
        db_session.add(job)
        db_session.commit()
        
        # Valid transitions
        job.status = JobStatus.QUEUED
        db_session.commit()
        assert job.status == JobStatus.QUEUED
        
        job.status = JobStatus.PROCESSING
        db_session.commit()
        assert job.status == JobStatus.PROCESSING
        
        job.status = JobStatus.COMPLETED
        db_session.commit()
        assert job.status == JobStatus.COMPLETED

    def test_video_file_relationship(self, db_session):
        job = Job(type=JobType.RESTORATION, status=JobStatus.PENDING)
        db_session.add(job)
        db_session.flush()
        
        video_file = VideoFile(
            job_id=job.id,
            original_filename="test.mp4",
            original_path="/tmp/test.mp4",
            file_size=1000,
        )
        db_session.add(video_file)
        db_session.commit()
        
        # Test relationship
        db_session.refresh(job)
        assert len(job.files) == 1
        assert job.files[0].original_filename == "test.mp4"
        
        # Test cascade delete
        db_session.delete(job)
        db_session.commit()
        remaining = db_session.query(VideoFile).filter(VideoFile.job_id == job.id).all()
        assert len(remaining) == 0

    def test_job_event_logging(self, db_session):
        job = Job(type=JobType.RESTORATION, status=JobStatus.PENDING)
        db_session.add(job)
        db_session.flush()
        
        from app.models import JobEvent
        event = JobEvent(
            job_id=job.id,
            event_type="status_change",
            message="Job queued",
        )
        db_session.add(event)
        db_session.commit()
        
        db_session.refresh(job)
        assert len(job.events) == 1
        assert job.events[0].event_type == "status_change"

    def test_video_file_status_enum(self, db_session):
        job = Job(type=JobType.RESTORATION, status=JobStatus.PENDING)
        db_session.add(job)
        db_session.flush()
        
        # Use JobStatus values since VideoFile.status uses JobStatus enum
        for status in [JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED]:
            video_file = VideoFile(
                job_id=job.id,
                original_filename=f"test_{status.value}.mp4",
                original_path=f"/tmp/test_{status.value}.mp4",
                file_size=1000,
                status=status,
            )
            db_session.add(video_file)
        
        db_session.commit()
        
        files = db_session.query(VideoFile).filter(VideoFile.job_id == job.id).all()
        assert len(files) == 4
        statuses = {f.status for f in files}
        assert statuses == {JobStatus.PENDING, JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED}