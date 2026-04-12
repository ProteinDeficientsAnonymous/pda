from community.api import router as community_router
from django.urls import path, re_path
from django.views.generic import TemplateView
from ninja import NinjaAPI
from notifications.api import router as notifications_router
from users.api import router as auth_router

from config.media_proxy import serve_media


class NoCacheTemplateView(TemplateView):
    """TemplateView that sets Cache-Control: no-cache so browsers always revalidate."""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-cache"
        return response


api = NinjaAPI(title="PDA API", version="1.0.0")
api.add_router("/auth/", auth_router, tags=["auth"])
api.add_router("/community/", community_router, tags=["community"])
api.add_router("/notifications/", notifications_router, tags=["notifications"])

urlpatterns = [
    path("api/", api.urls),
    # Media proxy — streams files from storage backend (local disk or B2)
    re_path(r"^media/(?P<path>.+)$", serve_media),
    # Flutter SPA catch-all (MUST BE LAST)
    # no-cache ensures browsers always check for new builds after deploys
    re_path(
        r"^(?!.*\.(js|css|json|wasm|png|jpg|ico|svg|ttf|otf|woff|woff2|map)$).*$",
        NoCacheTemplateView.as_view(template_name="flutter/index.html"),
    ),
]
