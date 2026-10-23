import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_app = get_asgi_application()

from mcp_gateway.asgi_router import McpDispatcher  # noqa: E402
from mcp_gateway.server import mcp_app  # noqa: E402

application = McpDispatcher(django_app, mcp_app)
