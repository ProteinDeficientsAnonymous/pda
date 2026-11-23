from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self) -> None:
        from config.jwt_backend import install_legacy_key_backend

        install_legacy_key_backend()
