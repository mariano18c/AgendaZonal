"""Geographic utilities for AgendaZonal.

Uses Haversine formula for distance calculations.
Bounding box for fast pre-filtering before precise distance check.
"""
import math
from dataclasses import dataclass

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0


@dataclass
class BoundingBox:
    """Geographic bounding box for efficient spatial filtering."""
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points on Earth using Haversine formula.

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in kilometers
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


def bounding_box(center_lat: float, center_lon: float, radius_km: float) -> BoundingBox:
    """Calculate a bounding box around a center point.

    This creates a square that encloses the circular area of the given radius.
    Used for fast database filtering before applying precise Haversine distance.

    Args:
        center_lat: Center latitude (degrees)
        center_lon: Center longitude (degrees)
        radius_km: Radius in kilometers

    Returns:
        BoundingBox with lat/lon min/max
    """
    # ~111 km per degree of latitude (varies slightly by location)
    lat_delta = radius_km / 111.0

    # Longitude degrees per km varies by latitude
    # At equator: ~111 km/degree, decreases toward poles
    cos_lat = math.cos(math.radians(center_lat))
    if abs(cos_lat) < 0.0001:  # Near poles (not applicable for Argentina)
        lon_min = -180.0
        lon_max = 180.0
    else:
        lon_delta = radius_km / (111.0 * cos_lat)
        lon_min = max(center_lon - lon_delta, -180.0)
        lon_max = min(center_lon + lon_delta, 180.0)

    return BoundingBox(
        lat_min=center_lat - lat_delta,
        lat_max=center_lat + lat_delta,
        lon_min=lon_min,
        lon_max=lon_max,
    )


def is_within_radius(
    center_lat: float, center_lon: float,
    point_lat: float, point_lon: float,
    radius_km: float,
) -> bool:
    """Check if a point is within radius of a center point.

    Args:
        center_lat, center_lon: Center coordinates
        point_lat, point_lon: Point to check
        radius_km: Maximum distance in km

    Returns:
        True if point is within radius
    """
    return haversine_km(center_lat, center_lon, point_lat, point_lon) <= radius_km


def validate_coordinates(lat: float | None, lon: float | None) -> bool:
    """Validate that coordinates are valid geographic coordinates.

    Args:
        lat: Latitude (-90 to 90) or None
        lon: Longitude (-180 to 180) or None

    Returns:
        True if both are valid or both are None
    """
    if lat is None and lon is None:
        return True
    if lat is None or lon is None:
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180
