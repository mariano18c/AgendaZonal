"""Unit tests for the badge service."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.services.badge_service import BADGE_DEFINITIONS
from app.schemas.badge import BadgeType, BadgeSchema


def test_badge_definitions():
    """Test that all badge types have definitions."""
    for badge_type in BadgeType:
        assert badge_type in BADGE_DEFINITIONS
        definition = BADGE_DEFINITIONS[badge_type]
        assert "name" in definition
        assert "description" in definition
        assert "icon" in definition


def test_badge_schema_creation():
    """Test that we can create a BadgeSchema instance."""
    badge = BadgeSchema(
        type=BadgeType.PRIMER_LEAD,
        name="Test Badge",
        description="Test Description",
        icon="🏆",
        is_earned=True,
        earned_at=datetime.now(timezone.utc)
    )
    
    assert badge.type == BadgeType.PRIMER_LEAD
    assert badge.name == "Test Badge"
    assert badge.description == "Test Description"
    assert badge.icon == "🏆"
    assert badge.is_earned == True
    assert badge.earned_at is not None


def test_badge_schema_defaults():
    """Test BadgeSchema with default values."""
    badge = BadgeSchema(
        type=BadgeType.LEADS_10,
        name="Test Badge",
        description="Test Description",
        icon="🏆"
    )
    
    assert badge.type == BadgeType.LEADS_10
    assert badge.name == "Test Badge"
    assert badge.description == "Test Description"
    assert badge.icon == "🏆"
    assert badge.is_earned == False  # default
    assert badge.earned_at is None  # default