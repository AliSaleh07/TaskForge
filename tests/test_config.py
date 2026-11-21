"""Test configuration loading and environment parsing for TaskForge."""

import os
from importlib import reload
import pytest
import taskforge.config


def test_cors_origins_dev_fallback():
    # Development mode falls back to localhost defaults
    os.environ["TASKFORGE_ENV"] = "development"
    os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
    os.environ.pop("TASKFORGE_SECRET_KEY", None)
    reload(taskforge.config)
    assert "http://localhost:8000" in taskforge.config.settings.ALLOWED_ORIGINS


def test_cors_origins_custom_override():
    os.environ["TASKFORGE_ENV"] = "development"
    os.environ["TASKFORGE_ALLOWED_ORIGINS"] = "https://taskforge.salehsec.dev, https://salehsec.dev"
    try:
        reload(taskforge.config)
        assert taskforge.config.settings.ALLOWED_ORIGINS == [
            "https://taskforge.salehsec.dev",
            "https://salehsec.dev",
        ]
    finally:
        os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        reload(taskforge.config)


def test_cors_origins_production_rejects_missing_origins():
    os.environ["TASKFORGE_ENV"] = "production"
    os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
    os.environ["TASKFORGE_SECRET_KEY"] = "a-long-enough-production-secret-key-at-least-32-characters"
    try:
        with pytest.raises(ValueError, match="TASKFORGE_ALLOWED_ORIGINS environment variable is mandatory"):
            reload(taskforge.config)
    finally:
        os.environ["TASKFORGE_ENV"] = "development"
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        reload(taskforge.config)


def test_cors_origins_production_rejects_localhost():
    os.environ["TASKFORGE_ENV"] = "production"
    os.environ["TASKFORGE_ALLOWED_ORIGINS"] = "https://salehsec.dev, http://localhost:3000"
    os.environ["TASKFORGE_SECRET_KEY"] = "a-long-enough-production-secret-key-at-least-32-characters"
    try:
        with pytest.raises(ValueError, match="Localhost origins are forbidden in production"):
            reload(taskforge.config)
    finally:
        os.environ["TASKFORGE_ENV"] = "development"
        os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        reload(taskforge.config)


def test_cors_origins_production_accepts_valid_origins():
    os.environ["TASKFORGE_ENV"] = "production"
    os.environ["TASKFORGE_ALLOWED_ORIGINS"] = "https://taskforge.salehsec.dev, https://salehsec.dev"
    os.environ["TASKFORGE_SECRET_KEY"] = "a-long-enough-production-secret-key-at-least-32-characters"
    try:
        reload(taskforge.config)
        assert taskforge.config.settings.ALLOWED_ORIGINS == [
            "https://taskforge.salehsec.dev",
            "https://salehsec.dev",
        ]
    finally:
        os.environ["TASKFORGE_ENV"] = "development"
        os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        reload(taskforge.config)


# --- SECRET_KEY validation tests ---

def test_secret_key_production_rejects_missing():
    """Production startup must fail if TASKFORGE_SECRET_KEY is not set."""
    os.environ["TASKFORGE_ENV"] = "production"
    os.environ.pop("TASKFORGE_SECRET_KEY", None)
    os.environ["TASKFORGE_ALLOWED_ORIGINS"] = "https://salehsec.dev"
    try:
        with pytest.raises(ValueError, match="TASKFORGE_SECRET_KEY environment variable is required in production"):
            reload(taskforge.config)
    finally:
        os.environ["TASKFORGE_ENV"] = "development"
        os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        reload(taskforge.config)


def test_secret_key_production_rejects_insecure_default():
    """Production startup must reject the known insecure default secret key."""
    os.environ["TASKFORGE_ENV"] = "production"
    os.environ["TASKFORGE_SECRET_KEY"] = "insecure-default-change-in-production-k7z9v8w2q1"
    os.environ["TASKFORGE_ALLOWED_ORIGINS"] = "https://salehsec.dev"
    try:
        with pytest.raises(ValueError, match="TASKFORGE_SECRET_KEY matches a known insecure default"):
            reload(taskforge.config)
    finally:
        os.environ["TASKFORGE_ENV"] = "development"
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
        reload(taskforge.config)


def test_secret_key_production_rejects_short():
    """Production startup must reject SECRET_KEY shorter than 32 characters."""
    os.environ["TASKFORGE_ENV"] = "production"
    os.environ["TASKFORGE_SECRET_KEY"] = "too-short"
    os.environ["TASKFORGE_ALLOWED_ORIGINS"] = "https://salehsec.dev"
    try:
        with pytest.raises(ValueError, match="TASKFORGE_SECRET_KEY must be at least 32 characters"):
            reload(taskforge.config)
    finally:
        os.environ["TASKFORGE_ENV"] = "development"
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
        reload(taskforge.config)


def test_secret_key_production_accepts_strong():
    """Production startup must accept a strong, unique, 32+ char secret key."""
    os.environ["TASKFORGE_ENV"] = "production"
    os.environ["TASKFORGE_SECRET_KEY"] = "a-long-enough-production-secret-key-at-least-32-characters"
    os.environ["TASKFORGE_ALLOWED_ORIGINS"] = "https://salehsec.dev"
    try:
        reload(taskforge.config)
        assert taskforge.config.settings.SECRET_KEY == "a-long-enough-production-secret-key-at-least-32-characters"
    finally:
        os.environ["TASKFORGE_ENV"] = "development"
        os.environ.pop("TASKFORGE_SECRET_KEY", None)
        os.environ.pop("TASKFORGE_ALLOWED_ORIGINS", None)
        reload(taskforge.config)


def test_secret_key_dev_allows_default():
    """Development mode must allow the insecure default for convenience."""
    os.environ["TASKFORGE_ENV"] = "development"
    os.environ.pop("TASKFORGE_SECRET_KEY", None)
    reload(taskforge.config)
    assert taskforge.config.settings.SECRET_KEY == "insecure-default-change-in-production-k7z9v8w2q1"
