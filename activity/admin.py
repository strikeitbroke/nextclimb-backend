from django.contrib import admin

from activity.models import EmailSignup, GeocodedLocation, SearchFeedback, StravaAuth


@admin.register(StravaAuth)
class StravaAuthAdmin(admin.ModelAdmin):
    list_display = ("id", "expires_at")


@admin.register(GeocodedLocation)
class GeocodedLocationAdmin(admin.ModelAdmin):
    list_display  = ("user_query", "latitude", "longitude", "created_at")
    search_fields = ("user_query",)
    ordering      = ("-created_at",)


@admin.register(SearchFeedback)
class SearchFeedbackAdmin(admin.ModelAdmin):
    list_display  = ("location", "radius", "vote", "comment", "created_at")
    list_filter   = ("vote",)
    search_fields = ("location", "comment")
    ordering      = ("-created_at",)


@admin.register(EmailSignup)
class EmailSignupAdmin(admin.ModelAdmin):
    list_display  = ("email", "created_at")
    ordering      = ("-created_at",)
