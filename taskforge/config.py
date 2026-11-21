"""Application configuration module for TaskForge."""

import os
from typing import List


class Settings:
    PROJECT_NAME: str = "TaskForge"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security & JWT
    SECRET_KEY: str = os.getenv("TASKFORGE_SECRET_KEY", "insecure-default-change-in-production-k7z9v8w2q1")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("TASKFORGE_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # Database
    DATABASE_PATH: str = os.getenv("TASKFORGE_DATABASE_PATH", "taskforge.db")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


settings = Settings()
