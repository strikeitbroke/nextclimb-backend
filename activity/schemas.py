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
    sw_lon: float
    ne_lat: float
    ne_lon: float

    def to_list(self) -> tuple[float, float, float, float]:
        """Returns the coordinates as a simple list."""
        return (self.sw_lat, self.sw_lon, self.ne_lat, self.ne_lon)


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
    elev_difference: float

    def to_miles(self) -> float:
        meters_in_mile = 1609.344
        return round(self.distance / meters_in_mile, 1)

    def to_km(self) -> float:
        return round(self.disance / 1000, 1)

    def get_difficulty(self) -> str:
        distance_km = self.distance / 1000
        gain_m = abs(self.elev_difference)
        avg_grade = abs(self.avg_grade)

        # 1. Base Score: (Gain is the foundation)
        score = gain_m * 1.0

        # 2. Steepness Multiplier:
        # If it's over 8%, every bit of grade hurts significantly more
        if avg_grade > 8:
            score += (avg_grade**2) * 2  # Exponential pain for steepness
        else:
            score += avg_grade * 15

        # 3. Sustained Effort:
        # Distance adds "fatigue," but we cap it so a flat 50km ride
        # doesn't get rated as "Brutal"
        score += min(distance_km * 25, 300)

        # 4. Overrides (The "Beginner Wall")
        if avg_grade >= 15:
            score += 300  # "The Wall" override
        if gain_m > 500:
            score += 200  # "Big Mountain" override

        # 5. Beginner-Centric Labels
        if score < 150:
            return "Easy"
        if score < 400:
            return "Moderate"
        if score < 800:
            return "Hard"
        return "Brutal"

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
    elev_difference: float
