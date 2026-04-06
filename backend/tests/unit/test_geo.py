"""Unit tests — geo utilities (Haversine, bounding box, validation)."""
import math
import pytest
from app.geo import haversine_km, bounding_box, is_within_radius, validate_coordinates


class TestHaversine:
    def test_same_point_zero(self):
        assert haversine_km(0, 0, 0, 0) == 0.0

    def test_known_distance_rosario(self):
        # Rosario (-32.9468, -60.6393) to Buenos Aires (-34.6037, -58.3816)
        d = haversine_km(-32.9468, -60.6393, -34.6037, -58.3816)
        assert 270 < d < 310  # ~280 km

    def test_antipodal_points(self):
        d = haversine_km(0, 0, 0, 180)
        assert abs(d - math.pi * 6371) < 10

    def test_small_distance(self):
        # ~111 m (0.001 degree) near equator
        d = haversine_km(0, 0, 0.001, 0)
        assert 0.05 < d < 0.2

    def test_symmetry(self):
        d1 = haversine_km(10, 20, 30, 40)
        d2 = haversine_km(30, 40, 10, 20)
        assert abs(d1 - d2) < 0.001


class TestBoundingBox:
    def test_basic_box(self):
        bb = bounding_box(-32.9, -60.6, 10)
        assert bb.lat_min < -32.9 < bb.lat_max
        assert bb.lon_min < -60.6 < bb.lon_max

    def test_box_size(self):
        bb = bounding_box(0, 0, 100)
        # ~100 km / 111 km/degree ≈ 0.9 degrees
        lat_range = bb.lat_max - bb.lat_min
        assert 1.5 < lat_range < 2.0

    def test_near_pole(self):
        bb = bounding_box(89.999, 0, 10)
        # cos_lat ≈ 0 → lon spans full range
        assert bb.lon_min == -180.0

    def test_negative_coords(self):
        bb = bounding_box(-50, -70, 5)
        assert bb.lat_min < bb.lat_max
        assert bb.lon_min < bb.lon_max


class TestIsWithinRadius:
    def test_within(self):
        assert is_within_radius(0, 0, 0.01, 0.01, 10) is True

    def test_outside(self):
        assert is_within_radius(0, 0, 10, 10, 5) is False

    def test_exact_boundary(self):
        d = haversine_km(0, 0, 0.1, 0)
        assert is_within_radius(0, 0, 0.1, 0, d) is True


class TestValidateCoordinates:
    def test_valid(self):
        assert validate_coordinates(-32.9, -60.6) is True

    def test_both_none(self):
        assert validate_coordinates(None, None) is True

    def test_one_none(self):
        assert validate_coordinates(-32.9, None) is False
        assert validate_coordinates(None, -60.6) is False

    def test_out_of_range_lat(self):
        assert validate_coordinates(91, 0) is False
        assert validate_coordinates(-91, 0) is False

    def test_out_of_range_lon(self):
        assert validate_coordinates(0, 181) is False
        assert validate_coordinates(0, -181) is False

    def test_boundary_values(self):
        assert validate_coordinates(90, 180) is True
        assert validate_coordinates(-90, -180) is True
