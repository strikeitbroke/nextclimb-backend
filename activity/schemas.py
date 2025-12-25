from ninja import Schema


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


class SearchResponseSchema(Schema):
    id: int
    name: str
    difficulty: str
    distance: float
    avg_grade: float
