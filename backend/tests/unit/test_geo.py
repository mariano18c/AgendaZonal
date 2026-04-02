"""Tests for geo utilities — Haversine, bounding box, validation."""
import math
import pytest
from app.geo import haversine_km, bounding_box, is_within_radius, validate_coordinates


class TestHaversine:
    """Test Haversine distance calculation."""

    def test_same_point_returns_zero(self):
        dist = haversine_km(-32.95, -60.65, -32.95, -60.65)
        assert dist == pytest.approx(0.0, abs=0.01)

    def test_rosario_to_ibarlucea(self):
        """Real distance: Rosario Centro → Ibarlucea ≈ 15km."""
        # Rosario Centro: -32.95, -60.65
        # Ibarlucea: -32.85, -60.78
        dist = haversine_km(-32.95, -60.65, -32.85, -60.78)
        assert 10 < dist < 20  # ~15km with some margin

    def test_rosario_to_buenos_aires(self):
        """Real distance: Rosario → Buenos Aires ≈ 280km."""
        # Rosario: -32.95, -60.65
        # Buenos Aires: -34.60, -58.38
        dist = haversine_km(-32.95, -60.65, -34.60, -58.38)
        assert 250 < dist < 320  # ~280km with margin

    def test_symmetric(self):
        """Distance A→B should equal B→A."""
        d1 = haversine_km(-32.95, -60.65, -34.60, -58.38)
        d2 = haversine_km(-34.60, -58.38, -32.95, -60.65)
        assert d1 == pytest.approx(d2, abs=0.01)

    def test_antipodal_points(self):
        """Points on opposite sides of Earth ≈ 20,015km."""
        dist = haversine_km(0, 0, 0, 180)
        assert 20000 < dist < 20020

    def test_equator_one_degree(self):
        """1 degree longitude at equator ≈ 111.32km."""
        dist = haversine_km(0, 0, 0, 1)
        assert 111 < dist < 112


class TestBoundingBox:
    """Test bounding box calculation."""

    def test_center_included(self):
        """Center point should be within its own bounding box."""
        bbox = bounding_box(-32.95, -60.65, 10)
        assert bbox.lat_min <= -32.95 <= bbox.lat_max
        assert bbox.lon_min <= -60.65 <= bbox.lon_max

    def test_radius_affects_size(self):
        """Larger radius should produce larger bounding box."""
        bbox_small = bounding_box(-32.95, -60.65, 5)
        bbox_large = bounding_box(-32.95, -60.65, 20)
        assert bbox_large.lat_min < bbox_small.lat_min
        assert bbox_large.lat_max > bbox_small.lat_max
        assert bbox_large.lon_min < bbox_small.lon_min
        assert bbox_large.lon_max > bbox_small.lon_max

    def test_10km_radius_around_rosario(self):
        """10km radius around Rosario should produce reasonable bounds."""
        bbox = bounding_box(-32.95, -60.65, 10)
        # ~10km ≈ 0.09 degrees lat, ~0.09 degrees lon at this latitude
        assert abs(bbox.lat_max - (-32.95)) - 0.09 < 0.01
        assert abs(bbox.lat_min - (-32.95)) - 0.09 < 0.01

    def test_near_pole(self):
        """Near poles, lon_delta should be capped at 180."""
        bbox = bounding_box(89.0, 0, 1000)
        assert bbox.lon_min >= -180
        assert bbox.lon_max <= 180


class TestIsWithinRadius:
    """Test radius check."""

    def test_point_within_radius(self):
        """Point 5km away from center should be within 10km radius."""
        # Rosario Centro → slight offset (~5km)
        assert is_within_radius(-32.95, -60.65, -32.90, -60.65, 10) is True

    def test_point_outside_radius(self):
        """Buenos Aires should NOT be within 10km of Rosario."""
        assert is_within_radius(-32.95, -60.65, -34.60, -58.38, 10) is False

    def test_point_on_boundary(self):
        """Same point should be within any positive radius."""
        assert is_within_radius(-32.95, -60.65, -32.95, -60.65, 1) is True


class TestValidateCoordinates:
    """Test coordinate validation."""

    def test_valid_coordinates(self):
        assert validate_coordinates(-32.95, -60.65) is True

    def test_both_none(self):
        assert validate_coordinates(None, None) is True

    def test_only_lat(self):
        assert validate_coordinates(-32.95, None) is False

    def test_only_lon(self):
        assert validate_coordinates(None, -60.65) is False

    def test_lat_out_of_range(self):
        assert validate_coordinates(-91, -60.65) is False
        assert validate_coordinates(91, -60.65) is False

    def test_lon_out_of_range(self):
        assert validate_coordinates(-32.95, -181) is False
        assert validate_coordinates(-32.95, 181) is False

    def test_boundary_values(self):
        assert validate_coordinates(-90, -180) is True
        assert validate_coordinates(90, 180) is True
        assert validate_coordinates(0, 0) is True
