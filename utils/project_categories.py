"""Project category constants shared by project management flows."""

from __future__ import annotations

from typing import Any

PROJECT_CATEGORY_PENDING = "pending"
PROJECT_CATEGORY_PUBLISHED = "published"
PROJECT_CATEGORY_ARCHIVED = "archived"

DEFAULT_PROJECT_CATEGORY = PROJECT_CATEGORY_PENDING

PROJECT_CATEGORY_VALUES = (
    PROJECT_CATEGORY_PENDING,
    PROJECT_CATEGORY_PUBLISHED,
    PROJECT_CATEGORY_ARCHIVED,
)


def normalize_project_category(value: Any, fallback: str = DEFAULT_PROJECT_CATEGORY) -> str:
    """Normalize user/project category input to a supported value."""
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in PROJECT_CATEGORY_VALUES:
            return candidate
    return fallback


def is_valid_project_category(value: Any) -> bool:
    """Return True when value can be used as a persisted project category."""
    return isinstance(value, str) and value.strip().lower() in PROJECT_CATEGORY_VALUES
