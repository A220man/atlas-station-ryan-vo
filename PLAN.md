# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

skeleton-and-job-queue

## Roadmap

### skeleton-and-job-queue — FastAPI/React skeleton with job queue and video upload

Status: done

Acceptance:
- FastAPI backend starts and serves health endpoint
- React frontend builds and loads
- Video upload API accepts files and creates job records
- Job queue processes uploads with basic status tracking
- Frontend shows upload form and job list with status
- Docker Compose runs backend, frontend, and Keycloak

Implementation: `backend/app/main.py`, `backend/app/models/__init__.py`, `backend/app/api/jobs.py`, `backend/app/services/video_processor.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/vite.config.ts`, `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `.github/workflows/ci.yml`

Tests: `backend/tests/test_api.py`, `backend/tests/test_models.py`, `backend/tests/test_services.py`, `backend/tests/conftest.py`, `frontend/src/App.test.tsx`, `frontend/vitest.config.ts`

### video-restoration-pipeline — Core video restoration pipeline with FFmpeg/PyAV

Status: planned

Acceptance:
- Pipeline accepts job, runs deblocking/denoising via FFmpeg
- Progress updates streamed to frontend via WebSocket or polling
- Completed jobs produce downloadable output files
- SAR handling fix for undeclared aspect ratios
- CPU encoding fallback (libx265) when NVENC unavailable

### oidc-auth-keycloak — OIDC authentication with Keycloak

Status: planned

Acceptance:
- Login redirects to Keycloak, callback exchanges code for tokens
- Backend validates JWT with signature/issuer/audience checks
- Frontend stores tokens in memory (not localStorage)
- Protected endpoints reject unauthenticated requests
- Role-based access: viewer/operator/admin

### ltx-model-integration — LTX model integration for AI-based restoration

Status: planned

Acceptance:
- LTX model loads and runs inference on uploaded clips
- Model feedback collection endpoint (issue #489)
- Opt-in LLM explanations for restoration decisions
- Provider-agnostic LLM adapter (OpenAI-compatible, Anthropic, Gemini)

### pause-resume-skip — Pause/resume and skip completed files

Status: planned

Acceptance:
- Jobs can be paused and resumed from checkpoint
- Already-processed files skipped on restart (issue #364)
- Partial progress persisted to database

### vr180-grid-fix — VR180 grid pattern artifact fix

Status: planned

Acceptance:
- SBS+Fisheye mode processes without grid artifacts (issue #354)
- Per-eye mode continues working
- Documented limitation/workaround for affected content

### amd-amf-support — AMD/AMF encoder fixes and AV1 10-bit support

Status: planned

Acceptance:
- SAR crash fixed for undeclared aspect ratios (issue #471)
- AV1 AMF encoder initializes with working parameters
- Documented working parameter combinations

### container-activation — gVisor/Modal container activation support

Status: planned

Acceptance:
- Machine identity derivation works in gVisor sandboxes (issue #525)
- Offline --machine-key works without persistent hardware ID
- Cloud workspace activation documented for ephemeral containers

### frame-interpolation — Single-pass frame interpolation

Status: planned

Acceptance:
- RIFE or FILM model integrated for interpolation
- Single encoding pass for deblocking + interpolation (issue #365)
- Configurable target FPS and quality

