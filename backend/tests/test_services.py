import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.video_processor import (
    probe_video, has_nvenc, has_amf, get_best_encoder,
    build_restoration_filterchain, process_job, create_job_from_upload
)
from app.models import Job, VideoFile, JobStatus, JobType
from app.api.schemas import VideoFileStatus


class TestEncoderDetection:
    @patch("app.services.video_processor.subprocess.run")
    def test_has_nvenc_true(self, mock_run):
        mock_run.return_value = MagicMock(stdout="hevc_nvenc\nh264_nvenc\n", returncode=0)
        assert has_nvenc() is True

    @patch("app.services.video_processor.subprocess.run")
    def test_has_nvenc_false(self, mock_run):
        mock_run.return_value = MagicMock(stdout="libx264\nlibx265\n", returncode=0)
        assert has_nvenc() is False

    @patch("app.services.video_processor.subprocess.run")
    def test_has_amf_true(self, mock_run):
        mock_run.return_value = MagicMock(stdout="hevc_amf\nh264_amf\n", returncode=0)
        assert has_amf() is True

    @patch("app.services.video_processor.subprocess.run")
    def test_get_best_encoder_nvenc(self, mock_run):
        mock_run.return_value = MagicMock(stdout="hevc_nvenc\n", returncode=0)
        assert get_best_encoder("hevc") == "hevc_nvenc"

    @patch("app.services.video_processor.has_nvenc", return_value=False)
    @patch("app.services.video_processor.has_amf", return_value=False)
    def test_get_best_encoder_cpu_fallback(self, mock_amf, mock_nvenc):
        assert get_best_encoder("hevc") == "libx265"
        assert get_best_encoder("h264") == "libx264"
        assert get_best_encoder("av1") == "libsvtav1"


class TestFilterChain:
    def test_build_restoration_filterchain_basic(self):
        options = {"deblock": True, "denoise": True}
        chain = build_restoration_filterchain(options)
        assert "deblock" in chain
        assert "nlmeans" in chain or "hqdn3d" in chain
        assert "setsar=1" in chain  # SAR fix for issue #471

    def test_build_restoration_filterchain_no_deblock(self):
        options = {"deblock": False, "denoise": True}
        chain = build_restoration_filterchain(options)
        assert "deblock" not in chain
        assert "setsar=1" in chain

    def test_build_restoration_filterchain_scaling(self):
        options = {"target_width": 1920, "target_height": 1080}
        chain = build_restoration_filterchain(options)
        assert "scale=1920:1080" in chain
        assert "pad=1920:1080" in chain


class TestJobCreation:
    def test_create_job_from_upload(self, db_session):
        fake_content = b"fake video data"
        files = [("test.mp4", fake_content)]
        
        with patch("app.services.video_processor.probe_video") as mock_probe:
            mock_probe.return_value = {
                "duration": 10.0,
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "codec": "h264",
                "has_audio": 1,
            }
            
            job = create_job_from_upload(db_session, files, JobType.RESTORATION, {"crf": 20})
            
            assert job.id is not None
            assert job.type == JobType.RESTORATION
            assert job.status == JobStatus.QUEUED
            assert job.options_json is not None
            options = json.loads(job.options_json)
            assert options["crf"] == 20
            
            # Check video file was created
            video_files = db_session.query(VideoFile).filter(VideoFile.job_id == job.id).all()
            assert len(video_files) == 1
            vf = video_files[0]
            assert vf.original_filename == "test.mp4"
            assert vf.width == 1920
            assert vf.height == 1080
            assert vf.has_audio == 1


class TestJobProcessing:
    @patch("app.services.video_processor.subprocess.Popen")
    def test_process_job_success(self, mock_popen, db_session):
        # Create a job with a video file
        job = Job(
            id="test-job-id",
            type=JobType.RESTORATION,
            status=JobStatus.QUEUED,
            input_dir="/tmp/test",
            options_json=json.dumps({"crf": 23}),
        )
        db_session.add(job)
        
        video_file = VideoFile(
            id="test-file-id",
            job_id=job.id,
            original_filename="test.mp4",
            original_path="/tmp/test/test.mp4",
            file_size=1000,
            has_audio=0,
        )
        db_session.add(video_file)
        db_session.commit()
        
        # Mock successful FFmpeg run
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        
        # Mock output file creation
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 2000
            with patch("pathlib.Path.mkdir"):
                with patch("pathlib.Path.exists", return_value=True):
                    process_job(job, db_session)
        
        db_session.refresh(job)
        db_session.refresh(video_file)
        
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 1.0
        assert video_file.status == VideoFileStatus.COMPLETED
        assert video_file.output_size == 2000

    @patch("app.services.video_processor.subprocess.Popen")
    def test_process_job_failure(self, mock_popen, db_session):
        job = Job(
            id="test-job-id-2",
            type=JobType.RESTORATION,
            status=JobStatus.QUEUED,
            input_dir="/tmp/test",
            options_json=json.dumps({}),
        )
        db_session.add(job)
        
        video_file = VideoFile(
            id="test-file-id-2",
            job_id=job.id,
            original_filename="test.mp4",
            original_path="/tmp/test/test.mp4",
            file_size=1000,
        )
        db_session.add(video_file)
        db_session.commit()
        
        # Mock failed FFmpeg run
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "FFmpeg error")
        mock_proc.returncode = 1
        mock_popen.return_value = mock_proc
        
        with patch("pathlib.Path.mkdir"):
            process_job(job, db_session)
        
        db_session.refresh(job)
        db_session.refresh(video_file)
        
        assert job.status == JobStatus.FAILED
        assert video_file.status == VideoFileStatus.FAILED
        assert "FFmpeg error" in video_file.error_message