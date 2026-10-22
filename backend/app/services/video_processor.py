import os
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy.orm import Session

from app.models import Job, VideoFile, JobStatus, JobEvent, JobType
from app.api.schemas import VideoFileStatus
from app.core.config import get_settings


settings = get_settings()


def probe_video(file_path: Path) -> Dict[str, Any]:
    """Extract video metadata using ffprobe."""
    cmd = [
        settings.ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {}
        import json as json_module
        data = json_module.loads(result.stdout)
        
        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
        
        return {
            "duration": float(video_stream.get("duration", data.get("format", {}).get("duration", 0))),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream.get("r_frame_rate") else None,
            "codec": video_stream.get("codec_name"),
            "has_audio": 1 if audio_stream else 0,
            "format": data.get("format", {}).get("format_name"),
        }
    except Exception:
        return {}


def has_nvenc() -> bool:
    """Check if NVENC is available on the system."""
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        return "hevc_nvenc" in result.stdout or "h264_nvenc" in result.stdout
    except Exception:
        return False


def has_amf() -> bool:
    """Check if AMD AMF encoders are available."""
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-encoders"],
            capture_output=True, text=True, timeout=10
        )
        return "hevc_amf" in result.stdout or "h264_amf" in result.stdout or "av1_amf" in result.stdout
    except Exception:
        return False


def get_best_encoder(codec: str = "hevc") -> str:
    """Get the best available encoder for the given codec."""
    # Priority: NVENC > AMF > CPU (libx265/libx264)
    if has_nvenc():
        return f"{codec}_nvenc"
    if has_amf():
        return f"{codec}_amf"
    # CPU fallback
    if codec == "hevc":
        return "libx265"
    if codec == "h264":
        return "libx264"
    if codec == "av1":
        return "libsvtav1"
    return "libx265"


def build_restoration_filterchain(options: Dict[str, Any]) -> str:
    """Build FFmpeg filter chain for video restoration."""
    filters = []
    
    # Deblocking
    if options.get("deblock", True):
        strength = options.get("deblock_strength", 3)
        filters.append(f"deblock={strength}:{strength}")
    
    # Denoising
    if options.get("denoise", True):
        method = options.get("denoise_method", "nlmeans")
        if method == "nlmeans":
            strength = options.get("denoise_strength", 3)
            filters.append(f"nlmeans={strength}:{strength}:7:15:0:0")
        elif method == "hqdn3d":
            strength = options.get("denoise_strength", 3)
            filters.append(f"hqdn3d={strength}:{strength}:{strength}:{strength}")
    
    # SAR fix for undeclared aspect ratios (issue #471)
    filters.append("setsar=1")
    
    # Scale/crop if needed
    if options.get("target_width") and options.get("target_height"):
        filters.append(f"scale={options['target_width']}:{options['target_height']}:force_original_aspect_ratio=decrease")
        filters.append(f"pad={options['target_width']}:{options['target_height']}:(ow-iw)/2:(oh-ih)/2")
    
    return ",".join(filters) if filters else "null"


def process_job(job: Job, db: Session) -> None:
    """Main job processing function. Runs synchronously in background worker."""
    job.status = JobStatus.PROCESSING
    job.started_at = datetime.now(timezone.utc)
    job.current_step = "initializing"
    db.commit()
    
    try:
        input_dir = Path(job.input_dir) if job.input_dir else settings.upload_path / job.id
        output_dir = Path(job.output_dir) if job.output_dir else settings.output_path / job.id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        options = json.loads(job.options_json) if job.options_json else {}
        encoder = get_best_encoder(options.get("output_codec", "hevc"))
        
        # Process each file
        for video_file in job.files:
            video_file.status = VideoFileStatus.PROCESSING
            video_file.progress = 0.0
            db.commit()
            
            input_path = Path(video_file.original_path)
            output_filename = f"restored_{video_file.original_filename}"
            output_path = output_dir / output_filename
            
            job.current_step = f"processing {video_file.original_filename}"
            video_file.current_step = "encoding"
            db.commit()
            
            # Build FFmpeg command
            filter_chain = build_restoration_filterchain(options)
            
            cmd = [
                settings.ffmpeg_path,
                "-y",  # Overwrite output
                "-i", str(input_path),
                "-vf", filter_chain,
                "-c:v", encoder,
                "-preset", options.get("encoder_preset", "medium"),
                "-crf", str(options.get("crf", 23)),
            ]
            
            # Audio handling
            if video_file.has_audio:
                cmd.extend(["-c:a", "copy"])
            else:
                cmd.extend(["-an"])
            
            cmd.append(str(output_path))
            
            # Run FFmpeg with progress tracking
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                
                # Monitor progress (simplified - real implementation would parse stderr)
                stdout, stderr = proc.communicate(timeout=3600)
                
                if proc.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {stderr[:500]}")
                
                # Update file record
                video_file.status = VideoFileStatus.COMPLETED
                video_file.progress = 1.0
                video_file.output_path = str(output_path)
                video_file.output_size = output_path.stat().st_size
                video_file.processed_at = datetime.now(timezone.utc)
                
                # Log event
                db.add(JobEvent(
                    job_id=job.id,
                    event_type="file_completed",
                    message=f"Completed processing {video_file.original_filename}",
                    data_json=json.dumps({"file_id": video_file.id, "output_path": str(output_path)})
                ))
                
            except subprocess.TimeoutExpired:
                proc.kill()
                raise RuntimeError(f"Processing timeout for {video_file.original_filename}")
            except Exception as e:
                video_file.status = VideoFileStatus.FAILED
                video_file.error_message = str(e)
                db.add(JobEvent(
                    job_id=job.id,
                    event_type="file_failed",
                    message=f"Failed processing {video_file.original_filename}: {e}",
                    data_json=json.dumps({"file_id": video_file.id, "error": str(e)})
                ))
                raise
            
            db.commit()
        
        # All files done
        job.status = JobStatus.COMPLETED
        job.progress = 1.0
        job.completed_at = datetime.now(timezone.utc)
        job.current_step = "completed"
        job.output_dir = str(output_dir)
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now(timezone.utc)
        db.add(JobEvent(
            job_id=job.id,
            event_type="job_failed",
            message=f"Job failed: {e}",
            data_json=json.dumps({"error": str(e)})
        ))
    
    db.commit()


def create_job_from_upload(
    db: Session,
    files: List[tuple[str, bytes]],  # (filename, content)
    job_type: JobType = JobType.RESTORATION,
    options: Optional[Dict[str, Any]] = None,
) -> Job:
    """Create a job from uploaded files."""
    job = Job(
        type=job_type,
        status=JobStatus.QUEUED,
        options_json=json.dumps(options) if options else None,
        input_dir=str(settings.upload_path),
    )
    db.add(job)
    db.flush()  # Get job.id
    
    # Save files and create VideoFile records
    job_upload_dir = settings.upload_path / job.id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    for filename, content in files:
        file_path = job_upload_dir / filename
        file_path.write_bytes(content)
        
        # Probe video metadata
        metadata = probe_video(file_path)
        
        video_file = VideoFile(
            job_id=job.id,
            original_filename=filename,
            original_path=str(file_path),
            file_size=len(content),
            duration=metadata.get("duration"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            fps=metadata.get("fps"),
            codec=metadata.get("codec"),
            has_audio=metadata.get("has_audio", 0),
        )
        db.add(video_file)
    
    job.input_dir = str(job_upload_dir)
    db.commit()
    db.refresh(job)
    
    return job