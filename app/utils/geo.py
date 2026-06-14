from typing import Optional, Tuple
from shapely.geometry import Point
from geoalchemy2.shape import to_shape, from_shape


def point_to_wkt(lng: float, lat: float) -> str:
    return f"SRID=4326;POINT({lng} {lat})"


def wkt_to_point(wkt: str) -> Optional[Tuple[float, float]]:
    try:
        point = to_shape(wkt)
        return (point.x, point.y)
    except Exception:
        return None


def make_geo_point(lng: float, lat: float):
    point = Point(lng, lat)
    return from_shape(point, srid=4326)


def get_geo_point_coords(geo_value) -> Optional[dict]:
    if not geo_value:
        return None
    try:
        point = to_shape(geo_value)
        return {"lng": point.x, "lat": point.y}
    except Exception:
        return None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    R = 6371000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
