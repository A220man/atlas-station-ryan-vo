from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import init_db
from app.api import jobs


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="Atlas Station",
    description="Video restoration and enhancement platform",
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(jobs.router)


# Static files for frontend (in production)
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")


@app.get("/")
def root():
    return {
        "name": "Atlas Station",
        "version": settings.app_version,
        "description": "Video restoration and enhancement platform",
        "docs": "/docs",
        "health": "/api/v1/health",
    }