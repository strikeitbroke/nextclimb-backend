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
