"""TaskForge main FastAPI application entrypoint."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

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
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
)

# Mount local static directory for self-hosted, resilient Swagger UI & ReDoc assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Self-hosted Swagger UI to ensure reliable rendering without external CDN dependencies."""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """Self-hosted ReDoc documentation without external CDN or font dependencies."""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
        redoc_favicon_url="/static/favicon.png",
        with_google_fonts=False,
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
