from typing import Annotated, Any

from ninja import Schema
from pydantic import BeforeValidator


def unwrap_latlon(v: Any) -> tuple[float, float]:
    # Detect by class name string
    if type(v).__name__ == "LatLon":
        return tuple(v.root)

    # Standard list/tuple fallback
    if isinstance(v, (list, tuple)):
        return tuple(v)

    return v


# Create a reusable type for coordinates
LatLonSchema = Annotated[tuple[float, float], BeforeValidator(unwrap_latlon)]


class SegmentBoundsSchema(Schema):
    sw_lat: float
    sw_lng: float
    ne_lat: float
    ne_lng: float

    def to_list(self) -> list[float]:
        """Returns the coordinates as a simple list."""
        return [self.sw_lat, self.sw_lng, self.ne_lat, self.ne_lng]


class CoorsSchema(Schema):
    latitude: float
    longitude: float


class SearchPayloadSchema(Schema):
    location: str
    radius: int


class ExplorerSegment(Schema):
    id: int
    name: str
    climb_category: int
    climb_category_desc: str
    avg_grade: float
    distance: float
    start_latlng: LatLonSchema
    end_latlng: LatLonSchema

    def to_miles(self) -> float:
        meters_in_mile = 1609.344
        return round(self.distance / meters_in_mile, 1)

    def to_km(self) -> float:
        return round(self.disance / 1000, 1)

    def get_difficulty(self) -> str:
        if self.climb_category <= 2:
            return "Easy"
        elif self.climb_category == 3:
            return "Intermediate"
        else:
            return "Hard"

    class Config:
        from_attributes = True


class SearchResponseSchema(Schema):
    id: int
    name: str
    difficulty: str
    distance: float
    avg_grade: float
    start_latlng: LatLonSchema
    end_latlng: LatLonSchema
