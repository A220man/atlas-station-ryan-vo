from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional, Dict, Any
import json

from app.core.database import get_db, db_session
from app.models import Job, VideoFile, JobStatus, JobType, JobEvent
from app.api.schemas import (
    JobCreate, JobResponse, JobListResponse, VideoFileResponse, 
    JobEventResponse, HealthResponse, UploadResponse,
    VideoFileStatus,
)
from app.services.video_processor import create_job_from_upload, process_job, get_best_encoder


router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    from app.core.config import get_settings
    settings = get_settings()
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database=db_status,
    )


@router.post("/jobs/upload", response_model=UploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    job_type: str = Form("restoration"),
    options: str = Form("{}"),
    db: Session = Depends(get_db),
):
    """Upload video files and create a processing job."""
    # Validate files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Read file contents
    file_data = []
    total_size = 0
    max_size = 2048 * 1024 * 1024  # 2GB
    
    for upload_file in files:
        content = await upload_file.read()
        total_size += len(content)
        if total_size > max_size:
            raise HTTPException(status_code=413, detail="Total upload size exceeds 2GB limit")
        file_data.append((upload_file.filename or "unknown", content))
    
    # Parse options
    try:
        options_dict = json.loads(options)
    except json.JSONDecodeError:
        options_dict = {}
    
    # Create job
    job = create_job_from_upload(
        db=db,
        files=file_data,
        job_type=JobType(job_type),
        options=options_dict,
    )
    
    # Start background processing with a new database session
    def process_job_wrapper(job_id: str):
        with db_session() as bg_db:
            job = bg_db.query(Job).filter(Job.id == job_id).first()
            if job:
                process_job(job, bg_db)
    
    background_tasks.add_task(process_job_wrapper, job.id)
    # Return response
    video_files = db.query(VideoFile).filter(VideoFile.job_id == job.id).all()
    
    return UploadResponse(
        job_id=job.id,
        files=[VideoFileResponse.model_validate(f) for f in video_files],
    )


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[JobStatus] = None,
    db: Session = Depends(get_db),
):
    """List jobs with pagination and optional status filter."""
    query = db.query(Job)
    
    if status:
        query = query.filter(Job.status == status)
    
    total = query.count()
    jobs = query.order_by(desc(Job.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    
    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job details with files."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}/events", response_model=List[JobEventResponse])
def get_job_events(job_id: str, db: Session = Depends(get_db)):
    """Get job event log."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    events = db.query(JobEvent).filter(JobEvent.job_id == job_id).order_by(JobEvent.created_at).all()
    return [JobEventResponse.model_validate(e) for e in events]


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str, db: Session = Depends(get_db)):
    """Pause a running job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.PROCESSING, JobStatus.QUEUED):
        raise HTTPException(status_code=400, detail=f"Cannot pause job in status {job.status}")
    job.status = JobStatus.PAUSED
    db.commit()
    return {"status": "paused", "job_id": job_id}


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resume a paused job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail=f"Cannot resume job in status {job.status}")
    job.status = JobStatus.QUEUED
    db.commit()
    
    # Start background processing with a new database session
    def process_job_wrapper(job_id: str):
        with db_session() as bg_db:
            job = bg_db.query(Job).filter(Job.id == job_id).first()
            if job:
                process_job(job, bg_db)
    
    background_tasks.add_task(process_job_wrapper, job_id)
    return {"status": "resumed", "job_id": job_id}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancel a pending/queued/processing job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job in status {job.status}")
    job.status = JobStatus.CANCELLED
    # Mark pending files as cancelled
    for vf in job.files:
        if vf.status in (VideoFileStatus.PENDING, VideoFileStatus.PROCESSING):
            vf.status = VideoFileStatus.FAILED
            vf.error_message = "Job cancelled"
    db.commit()
    return {"status": "cancelled", "job_id": job_id}


@router.get("/encoders")
def list_encoders():
    """List available video encoders."""
    return {
        "hevc": get_best_encoder("hevc"),
        "h264": get_best_encoder("h264"),
        "av1": get_best_encoder("av1"),
        "nvenc_available": get_best_encoder("hevc").endswith("_nvenc"),
        "amf_available": get_best_encoder("hevc").endswith("_amf"),
    }