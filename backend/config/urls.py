from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView
from ninja import NinjaAPI
from ninja_jwt.authentication import JWTAuth

from community.api import router as community_router
from users.api import router as auth_router

api = NinjaAPI(title="PDA API", version="1.0.0")
api.add_router("/auth/", auth_router, tags=["auth"])
api.add_router("/community/", community_router, tags=["community"])

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
    # Flutter SPA catch-all (MUST BE LAST)
    re_path(
        r"^(?!.*\.(js|css|json|wasm|png|jpg|ico|svg|ttf|otf|woff|woff2|map)$).*$",
        TemplateView.as_view(template_name="flutter/index.html"),
    ),
]
