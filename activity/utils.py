import logging
import math
import re

from django.core.cache import cache
from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from typing_extensions import Sequence

from activity.models import GeocodedLocation
from activity.schemas import CoorsSchema, SearchResponseSchema, SegmentBoundsSchema

logger = logging.getLogger(__name__)


def get_coors(raw_query: str) -> CoorsSchema | None:
    # 1. Initialize the geocoding service
    # 'user_agent' is required; use your app's name
    geolocator = Nominatim(user_agent="nextclimb.fit", timeout=10)

    try:
        normalized_query = normalize_query(raw_query)
        existing = GeocodedLocation.objects.filter(user_query=normalized_query).first()
        if existing:
            logger.info("returning coordinates from local database.")
            return CoorsSchema(latitude=existing.latitude, longitude=existing.longitude)
        # 2. Perform the lookup
        location = geolocator.geocode(raw_query)

        if location:
            logger.info(f"get_coors: {location.latitude}, {location.longitude}")
            # 5. Save to DB
            GeocodedLocation.objects.create(
                user_query=normalized_query,
                latitude=location.latitude,
                longitude=location.longitude,
            )
            # Returns a tuple: (latitude, longitude)
            return CoorsSchema(latitude=location.latitude, longitude=location.longitude)

        logger.info("location is None")
        return None  # Return None if city not found

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.exception(f"Error: {e}")
        return None


def get_bounds(coors: CoorsSchema, radius: float) -> SegmentBoundsSchema:
    center = (coors.latitude, coors.longitude)

    # Note: For a "square" box with a 'radius', you actually go further
    # out to the corner than just the radius. We use radius * sqrt(2)
    # if you want the circle to be inside the box.
    corner_dist = geodesic(miles=radius * math.sqrt(2))

    # 1. Calculate Northeast corner (45 degrees)
    ne_point = corner_dist.destination(center, bearing=45)

    # 2. Calculate Southwest corner (225 degrees)
    sw_point = corner_dist.destination(center, bearing=225)
    print(
        f"bounds--> {sw_point.latitude}, {sw_point.longitude}, {ne_point.latitude}, {ne_point.longitude}"
    )
    # 3. Format exactly as Strava wants: "sw_lat,sw_lng,ne_lat,ne_lng"
    return SegmentBoundsSchema(
        sw_lat=sw_point.latitude,
        sw_lon=sw_point.longitude,
        ne_lat=ne_point.latitude,
        ne_lon=ne_point.longitude,
    )


def get_normalized_bounds(
    sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float, precision: int = 2
) -> tuple[float, float, float, float]:
    factor = 10**precision

    # SW: Move Down and Left (Floor)
    n_sw_lat = math.floor(sw_lat * factor) / factor
    n_sw_lon = math.floor(sw_lon * factor) / factor

    # NE: Move Up and Right (Ceiling)
    n_ne_lat = math.ceil(ne_lat * factor) / factor
    n_ne_lon = math.ceil(ne_lon * factor) / factor

    return n_sw_lat, n_sw_lon, n_ne_lat, n_ne_lon


def generate_cache_key(
    sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float
) -> str:
    n_sw_lat, n_sw_lon, n_ne_lat, n_ne_lon = get_normalized_bounds(
        sw_lat, sw_lon, ne_lat, ne_lon
    )
    return f"strava:{n_sw_lat}:{n_sw_lon}:{n_ne_lat}:{n_ne_lon}"


def get_cached_segments(
    sw_lat: float, sw_lon: float, ne_lat: float, ne_lon: float
) -> tuple[list[SearchResponseSchema], str]:
    # 1. Create the rounded key (2 decimal places ~1.1km precision)
    key = generate_cache_key(sw_lat, sw_lon, ne_lat, ne_lon)

    # 2. Return data if it exists, otherwise return None
    return cache.get(key), key


def set_cached_segments(key: str, data: Sequence[dict[str, object]]) -> None:
    # Cache for 24 hours (86400 seconds)
    cache.set(key, data, timeout=86400)


def normalize_query(query: str) -> str:
    # Lowercase, remove extra spaces, remove commas/dots
    query = query.lower().strip()
    query = re.sub(r"[,\.]", "", query)  # "san jose, ca" -> "san jose ca"
    query = " ".join(query.split())  # "san   jose" -> "san jose"
    return query
