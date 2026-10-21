from django.apps import AppConfig


class CommunityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "community"

    def ready(self):
        from config.media_proxy import preload_media_storage

        preload_media_storage()
