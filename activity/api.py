from ninja import Query, Router
from stravalib import Client

from activity.models import StravaAuth
from activity.schemas import (
    ExplorerSegment,
    SearchPayloadSchema,
    SearchResponseSchema,
    SegmentBoundsSchema,
)
from activity.utils import get_bounds, get_coors

router = Router()


@router.post("/")
def get_segment(request, payload: SegmentBoundsSchema):
    client = Client()
    strava_auth = StravaAuth.objects.get(id=1)
    strava_auth.check_and_refresh(client)

    client.access_token = strava_auth.access_token

    bounds = (payload.sw_lat, payload.sw_lng, payload.ne_lat, payload.ne_lng)

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
    bounds = get_bounds(coors, payload.radius)

    # data = [{"avg_grade": 10.2, "id": 1, "name": "Hawk hill", "distance": 3.2}]
    strava_explore_segments = client.explore_segments(
        bounds.to_list(), activity_type="riding", min_cat=1, max_cat=4
    )
    explore_segments: list[ExplorerSegment] = [
        ExplorerSegment(**s.__dict__) for s in strava_explore_segments
    ]
    response_schema = get_response_schema(explore_segments)
    data = [s.model_dump(mode="json") for s in response_schema]

    return data
