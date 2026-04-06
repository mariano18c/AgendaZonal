"""Unit tests — permission service + contacts permission functions."""
import pytest
from unittest.mock import MagicMock
from app.services.permission_service import can_edit_field, can_verify_change
from app.routes.contacts import can_edit_field as route_can_edit, can_verify_change as route_can_verify


def _user(role="user", user_id=1):
    u = MagicMock()
    u.id = user_id
    u.role = role
    return u


def _contact(owner_id=1):
    c = MagicMock()
    c.user_id = owner_id
    return c


class TestCanEditFieldService:
    """Tests for the service-layer permission function."""

    def test_no_user_empty_field(self):
        can, needs = can_edit_field(None, _contact(), "name", None)
        assert can is True and needs is True

    def test_no_user_empty_string(self):
        can, needs = can_edit_field(None, _contact(), "name", "")
        assert can is True and needs is True

    def test_no_user_filled_field(self):
        can, needs = can_edit_field(None, _contact(), "name", "Existing")
        assert can is False and needs is False

    def test_owner_any_field(self):
        can, needs = can_edit_field(_user(user_id=1), _contact(1), "name", "X")
        assert can is True and needs is False

    def test_admin_any_field(self):
        can, needs = can_edit_field(_user("admin", 99), _contact(1), "name", "X")
        assert can is True and needs is False

    def test_moderator_any_field(self):
        can, needs = can_edit_field(_user("moderator", 99), _contact(1), "name", "X")
        assert can is True and needs is False

    def test_other_user_empty_field(self):
        can, needs = can_edit_field(_user(user_id=99), _contact(1), "desc", None)
        assert can is True and needs is True

    def test_other_user_filled_field(self):
        can, needs = can_edit_field(_user(user_id=99), _contact(1), "desc", "Filled")
        assert can is False and needs is False


class TestCanVerifyChangeService:
    def test_no_user(self):
        assert can_verify_change(None, _contact()) is False

    def test_owner(self):
        assert can_verify_change(_user(user_id=1), _contact(1)) is True

    def test_admin(self):
        assert can_verify_change(_user("admin", 99), _contact(1)) is True

    def test_moderator(self):
        assert can_verify_change(_user("moderator", 99), _contact(1)) is True

    def test_other_user(self):
        assert can_verify_change(_user(user_id=99), _contact(1)) is False


class TestRouteCanEditField:
    """Same logic tested via the route-layer duplicate."""

    def test_owner_direct(self):
        can, needs = route_can_edit(_user(user_id=5), _contact(5), "name", "X")
        assert can is True and needs is False

    def test_anon_empty(self):
        can, needs = route_can_edit(None, _contact(5), "name", "")
        assert can is True and needs is True


class TestRouteCanVerifyChange:
    def test_mod(self):
        assert route_can_verify(_user("moderator", 5), _contact(1)) is True

    def test_stranger(self):
        assert route_can_verify(_user(user_id=5), _contact(1)) is False
