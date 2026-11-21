"""Authentication API router: user registration, login, and profile."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from taskforge.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from taskforge.config import settings
from taskforge.database import get_db
from taskforge.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest):
    """Register a new user account with strong password requirements."""
    user_id = str(uuid.uuid4())
    hashed = hash_password(req.password)
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        # Check uniqueness
        cursor.execute(
            "SELECT username, email FROM users WHERE username = ? OR email = ?",
            (req.username.lower(), req.email.lower()),
        )
        existing = cursor.fetchone()
        if existing:
            if existing["username"] == req.username.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username is already taken",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        cursor.execute(
            """
            INSERT INTO users (id, username, email, hashed_password, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'user', ?, ?)
            """,
            (user_id, req.username.lower(), req.email.lower(), hashed, now, now),
        )

    return UserResponse(
        id=user_id,
        username=req.username.lower(),
        email=req.email.lower(),
        role="user",
        created_at=now,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest):
    """Authenticate with username or email and receive a signed JWT."""
    identifier = req.username_or_email.lower().strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, hashed_password, role FROM users WHERE username = ? OR email = ?",
            (identifier, identifier),
        )
        user = cursor.fetchone()

    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        data={"sub": user["id"], "username": user["username"], "role": user["role"]},
        expires_delta_seconds=expires_seconds,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=expires_seconds,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve the currently authenticated user's profile."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=str(current_user["created_at"]),
    )
