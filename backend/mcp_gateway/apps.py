from django.apps import AppConfig


class McpGatewayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mcp_gateway"

    def ready(self) -> None:
        from mcp_gateway.tools import load_tools

        load_tools()
