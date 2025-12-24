from ninja import Query, Router
from stravalib import Client

from activity.models import StravaAuth
from activity.schemas import ExplorerSegment, SearchPayloadSchema, SegmentBoundsSchema
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


@router.get("/search")
def search(request, payload: Query[SearchPayloadSchema]):
    client = Client()
    strava_auth = StravaAuth.objects.get(id=1)
    strava_auth.check_and_refresh(client)

    client.access_token = strava_auth.access_token

    coors = get_coors(payload.location)
    bounds = get_bounds(coors, payload.radius)

    strava_explore_segments = client.explore_segments(
        bounds.to_list(), activity_type="riding", min_cat=1, max_cat=4
    )  # Get current athlete details
    explore_segments: list[ExplorerSegment] = [
        ExplorerSegment(**s.__dict__) for s in strava_explore_segments
    ]
    data = [s.model_dump(mode="json") for s in explore_segments]

    return data
