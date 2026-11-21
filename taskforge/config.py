"""Application configuration module for TaskForge."""

import os
from typing import List


# Known insecure default secret keys that must never be used in production
_INSECURE_SECRET_KEYS = [
    "insecure-default-change-in-production-k7z9v8w2q1",
    "secret",
    "changeme",
    "password",
    "your-secret-key",
    "jwt-secret",
]


class Settings:
    PROJECT_NAME: str = "TaskForge"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Environment mode
    ENV: str = os.getenv("TASKFORGE_ENV", os.getenv("ENVIRONMENT", "development")).lower()
    
    # Security & JWT
    SECRET_KEY: str = os.getenv("TASKFORGE_SECRET_KEY", "insecure-default-change-in-production-k7z9v8w2q1")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TASKFORGE_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Validate SECRET_KEY in production
    if ENV == "production":
        if not os.getenv("TASKFORGE_SECRET_KEY"):
            raise ValueError(
                "FATAL: TASKFORGE_SECRET_KEY environment variable is required in production."
            )
        if SECRET_KEY in _INSECURE_SECRET_KEYS:
            raise ValueError(
                "FATAL: TASKFORGE_SECRET_KEY matches a known insecure default. "
                "Use a cryptographically random value in production."
            )
        if len(SECRET_KEY) < 32:
            raise ValueError(
                "FATAL: TASKFORGE_SECRET_KEY must be at least 32 characters in production."
            )
    
    # Database path
    DATABASE_PATH: str = os.getenv("TASKFORGE_DATABASE_PATH", "taskforge.db")
    
    # CORS Origin Configuration
    raw_origins: str = os.getenv("TASKFORGE_ALLOWED_ORIGINS", "")
    
    if ENV == "production":
        parsed = [o.strip() for o in raw_origins.split(",") if o.strip()]
        if not parsed:
            raise ValueError(
                "FATAL: In production, TASKFORGE_ALLOWED_ORIGINS environment variable is mandatory "
                "and cannot be empty or fall back to localhost."
            )
        for o in parsed:
            if "localhost" in o or "127.0.0.1" in o:
                raise ValueError(
                    f"FATAL: Insecure origin '{o}' detected in production TASKFORGE_ALLOWED_ORIGINS. "
                    "Localhost origins are forbidden in production."
                )
        ALLOWED_ORIGINS: List[str] = parsed
    else:
        ALLOWED_ORIGINS: List[str] = (
            [o.strip() for o in raw_origins.split(",") if o.strip()]
            if raw_origins
            else [
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
        )


settings = Settings()
