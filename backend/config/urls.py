from community.api import router as community_router
from django.urls import path, re_path
from ninja import NinjaAPI
from notifications.api import router as notifications_router
from notifications.sse import notification_stream
from users.api import router as auth_router

from config.media_proxy import serve_media
from config.og_preview import event_og_preview
from config.validation_handlers import register_validation_handlers

api = NinjaAPI(title="PDA API", version="1.0.0")
register_validation_handlers(api)
api.add_router("/auth/", auth_router, tags=["auth"])
api.add_router("/community/", community_router, tags=["community"])
api.add_router("/notifications/", notifications_router, tags=["notifications"])

urlpatterns = [
    path("api/", api.urls),
    # SSE endpoint — raw async view (Ninja doesn't support streaming responses)
    path("api/notifications/stream/", notification_stream),
    # Media proxy — streams files from storage backend (local disk or B2)
    re_path(r"^media/(?P<path>.+)$", serve_media),
    # OG/Twitter meta tags for link scrapers. nginx routes /events/<id> here
    # only for scraper user-agents; real browsers get the SPA (see nginx.conf).
    path("events/<uuid:event_id>/preview/", event_og_preview),
]
