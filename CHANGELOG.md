# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-22

### Added
- Initial FastAPI backend with SQLite persistence
- React + TypeScript + Vite frontend with job dashboard
- Video upload API with multipart/form-data support
- Job queue with status tracking (pending/queued/processing/completed/failed/paused/cancelled)
- Background job processor with FFmpeg integration
- Hardware encoder detection (NVENC, AMF) with CPU fallback (libx265)
- SAR correction filter (`setsar=1`) for undeclared aspect ratios
- Pause/resume/cancel job controls
- Keycloak OIDC realm configuration with viewer/operator/admin roles
- Docker Compose with backend, frontend, and Keycloak services
- GitHub Actions CI workflow for backend/frontend tests and Docker builds
- Comprehensive test suite (backend: pytest, frontend: vitest)
- REST API with OpenAPI documentation at `/docs`

### Technical Details
- Backend: FastAPI, SQLAlchemy 2.0, PyAV/FFmpeg, httpx
- Frontend: React 18, TypeScript, TanStack Query, Zustand, Tailwind CSS (via custom CSS)
- Auth: SPA PKCE flow, tokens in memory, HttpOnly cookies for session
- Database: SQLite with Alembic-ready models
- File storage: Local filesystem with organized upload/output directories

### Known Limitations
- OIDC authentication endpoints not fully implemented (placeholder in frontend)
- LTX/RIFE AI models not yet integrated
- WebSocket progress updates not implemented (uses polling)
- Single-process worker (no Redis/Celery)
- SQLite not suitable for production concurrency