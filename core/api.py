from ninja import NinjaAPI

from activity.api import router as activity_router

api = NinjaAPI(title="NextClimb API")


api.add_router("/segment", activity_router)
