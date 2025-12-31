from ninja import Query, Router
from ninja.errors import HttpError
from stravalib import Client

from activity.models import StravaAuth
from activity.schemas import (
    ExplorerSegment,
    SearchPayloadSchema,
    SearchResponseSchema,
    SegmentBoundsSchema,
)
from activity.utils import (
    get_bounds,
    get_cached_segments,
    get_coors,
    set_cached_segments,
)

router = Router()


@router.post("/")
def get_segment(request, payload: SegmentBoundsSchema):
    client = Client()
    strava_auth = StravaAuth.objects.get(id=1)
    strava_auth.check_and_refresh(client)

    client.access_token = strava_auth.access_token

    bounds = (
        payload.sw_lat,
        payload.sw_lon,
        payload.ne_lat,
        payload.ne_lon,
    )

    segments = client.explore_segments(
        bounds, activity_type="riding", min_cat=1, max_cat=4
    )  # Get current athlete details
    data = [s.model_dump(mode="json") for s in segments]

    return data


def get_response_schema(explore_segments: list[ExplorerSegment]):
    response_schema: list[SearchResponseSchema] = []

    for item in explore_segments:
        response_schema.append(
            SearchResponseSchema(
                id=item.id,
                name=item.name,
                difficulty=item.get_difficulty(),
                distance=item.to_miles(),
                avg_grade=item.avg_grade,
                start_latlng=item.start_latlng,
                end_latlng=item.end_latlng,
            )
        )
    return response_schema


@router.get("/search")
def search(request, payload: Query[SearchPayloadSchema]):
    client = Client()
    strava_auth = StravaAuth.objects.get(id=1)
    strava_auth.check_and_refresh(client)

    client.access_token = strava_auth.access_token

    coors = get_coors(payload.location)
    if not coors:
        raise HttpError(500, "Coordinates could not be found for the provided location")

    bounds = get_bounds(coors, payload.radius)

    cached_data, cache_key = get_cached_segments(
        bounds.sw_lat, bounds.sw_lon, bounds.ne_lat, bounds.ne_lon
    )
    if cached_data:
        return {"source": "cached", "segments": cached_data}

    # data = [{"avg_grade": 10.2, "id": 1, "name": "Hawk hill", "distance": 3.2}]
    strava_explore_segments = client.explore_segments(
        bounds.to_list(), activity_type="riding", min_cat=1, max_cat=4
    )
    explore_segments: list[ExplorerSegment] = [
        ExplorerSegment(**s.__dict__) for s in strava_explore_segments
    ]
    response_schema = get_response_schema(explore_segments)
    data = [s.model_dump(mode="json") for s in response_schema]
    if data:
        set_cached_segments(cache_key, data)
    # data = [
    #     {
    #         "id": 627158,
    #         "name": "Montebello",
    #         "difficulty": "Intermediate",
    #         "distance": 5.1,
    #         "avg_grade": 8.1,
    #         "start_latlng": [37.8331119, -122.4834356],
    #         "end_latlng": [37.8280722, -122.4981393],
    #     },
    #     {
    #         "id": 8109834,
    #         "name": "Old La Honda (Bridge to Mailboxes)",
    #         "difficulty": "Easy",
    #         "distance": 3.1,
    #         "avg_grade": 7.8,
    #         "start_latlng": [37.8331119, -122.4834356],
    #         "end_latlng": [37.8280722, -122.4981393],
    #     },
    # ]
    return {"source": "strava", "segments": data}
