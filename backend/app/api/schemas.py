from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    RESTORATION = "restoration"
    INTERPOLATION = "interpolation"
    FEEDBACK = "feedback"


class VideoFileStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobCreate(BaseModel):
    type: JobType = JobType.RESTORATION
    options: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: JobType
    status: JobStatus
    progress: float
    current_step: Optional[str] = None
    error_message: Optional[str] = None
    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files: List["VideoFileResponse"] = []


class VideoFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    original_filename: str
    original_path: str
    file_size: int
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    has_audio: bool = False
    status: VideoFileStatus
    progress: float
    error_message: Optional[str] = None
    output_path: Optional[str] = None
    output_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None


class JobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    event_type: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    created_at: datetime


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


class UploadResponse(BaseModel):
    job_id: str
    files: List[VideoFileResponse]


# Forward reference resolution
JobResponse.model_rebuild()