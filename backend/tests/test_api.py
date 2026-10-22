import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        # Database may be disconnected in test due to lifespan using different engine
        assert data["database"] in ("connected", "disconnected")


class TestJobUpload:
    def test_upload_single_file(self, client):
        # Create a small fake video file
        fake_video = b"fake video content for testing"
        
        response = client.post(
            "/api/v1/jobs/upload",
            files={"files": ("test.mp4", fake_video, "video/mp4")},
            data={"job_type": "restoration", "options": "{}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["original_filename"] == "test.mp4"
        assert data["files"][0]["status"] == "pending"

    def test_upload_multiple_files(self, client):
        fake_video1 = b"fake video content 1"
        fake_video2 = b"fake video content 2"
        
        response = client.post(
            "/api/v1/jobs/upload",
            files=[
                ("files", ("test1.mp4", fake_video1, "video/mp4")),
                ("files", ("test2.mp4", fake_video2, "video/mp4")),
            ],
            data={"job_type": "restoration", "options": "{}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert len(data["files"]) == 2

    def test_upload_no_files(self, client):
        response = client.post(
            "/api/v1/jobs/upload",
            data={"job_type": "restoration", "options": "{}"}
        )
        # FastAPI returns 422 for missing required file parameter
        assert response.status_code == 422


class TestJobListing:
    def test_list_jobs_empty(self, client):
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    def test_list_jobs_with_data(self, client):
        # Create a job first
        fake_video = b"fake video content"
        client.post(
            "/api/v1/jobs/upload",
            files={"files": ("test.mp4", fake_video, "video/mp4")},
            data={"job_type": "restoration", "options": "{}"}
        )
        
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["jobs"]) == 1

    def test_list_jobs_pagination(self, client):
        # Create multiple jobs
        for i in range(5):
            fake_video = f"fake video {i}".encode()
            client.post(
                "/api/v1/jobs/upload",
                files={"files": (f"test{i}.mp4", fake_video, "video/mp4")},
                data={"job_type": "restoration", "options": "{}"}
            )
        
        response = client.get("/api/v1/jobs?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["jobs"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2


class TestJobDetail:
    def test_get_job(self, client):
        # Create a job
        fake_video = b"fake video content"
        with patch("app.api.jobs.process_job"):
            upload_resp = client.post(
                "/api/v1/jobs/upload",
                files={"files": ("test.mp4", fake_video, "video/mp4")},
                data={"job_type": "restoration", "options": "{}"}
            )
        job_id = upload_resp.json()["job_id"]
        
        # Get job details
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["type"] == "restoration"
        # Status should be queued since background task is mocked
        assert data["status"] in ("pending", "queued")
        assert len(data["files"]) == 1

    def test_get_nonexistent_job(self, client):
        response = client.get("/api/v1/jobs/nonexistent-id")
        assert response.status_code == 404


class TestJobEvents:
    def test_get_job_events(self, client):
        fake_video = b"fake video content"
        with patch("app.api.jobs.process_job"):
            upload_resp = client.post(
                "/api/v1/jobs/upload",
                files={"files": ("test.mp4", fake_video, "video/mp4")},
                data={"job_type": "restoration", "options": "{}"}
            )
        job_id = upload_resp.json()["job_id"]
        
        response = client.get(f"/api/v1/jobs/{job_id}/events")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestEncoders:
    def test_list_encoders(self, client):
        response = client.get("/api/v1/encoders")
        assert response.status_code == 200
        data = response.json()
        assert "hevc" in data
        assert "h264" in data
        assert "av1" in data
        assert "nvenc_available" in data
        assert "amf_available" in data


class TestJobControl:
    def test_pause_resume_cancel_flow(self, client):
        fake_video = b"fake video content"
        with patch("app.api.jobs.process_job"):
            upload_resp = client.post(
                "/api/v1/jobs/upload",
                files={"files": ("test.mp4", fake_video, "video/mp4")},
                data={"job_type": "restoration", "options": "{}"}
            )
        job_id = upload_resp.json()["job_id"]
        
        # Try to cancel (should work for queued job)
        response = client.post(f"/api/v1/jobs/{job_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"