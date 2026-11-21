"""TaskForge main FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from taskforge.config import settings
from taskforge.database import init_db
from taskforge.middleware import SecurityHeadersMiddleware
from taskforge.routers import auth, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    yield


app = FastAPI(
    title="TaskForge API",
    description="A secure, production-grade task management REST API built with FastAPI, SQLite, and PBKDF2/JWT authentication.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware configuration
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)


@app.get("/healthz", tags=["System"])
def health_check():
    """Health check endpoint for container orchestrators and uptime monitoring."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@app.get("/", tags=["System"])
def root():
    """API root redirect or welcome message."""
    return {
        "message": "Welcome to TaskForge REST API",
        "version": settings.VERSION,
        "documentation": "/docs",
        "health": "/healthz",
    }


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """Sanitize unexpected exceptions to prevent internal stack trace leakage."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Our team has been notified.",
            "type": "InternalServerError",
        },
    )
