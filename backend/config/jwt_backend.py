import warnings
from typing import Any

from django.conf import settings
from jwt import InvalidSignatureError
from jwt.warnings import InsecureKeyLengthWarning
from ninja_jwt import state
from ninja_jwt.backends import TokenBackend
from ninja_jwt.exceptions import TokenBackendError
from ninja_jwt.settings import api_settings


class LegacyKeyTokenBackend(TokenBackend):
    def __init__(self, *args: Any, legacy_signing_key: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.legacy = TokenBackend(
            self.algorithm,
            legacy_signing_key,
            audience=self.audience,
            issuer=self.issuer,
            leeway=self.leeway,
        )

    def decode(self, token: str, verify: bool = True) -> dict[str, Any]:
        try:
            return super().decode(token, verify=verify)
        except TokenBackendError as ex:
            if not isinstance(ex.__cause__, InvalidSignatureError):
                raise
        # The legacy key is known-short; its warning would just re-add the log noise.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureKeyLengthWarning)
            return self.legacy.decode(token, verify=verify)


def install_legacy_key_backend() -> None:
    legacy_key = settings.JWT_LEGACY_VERIFYING_KEY
    if not legacy_key:
        return
    state.token_backend = LegacyKeyTokenBackend(
        api_settings.ALGORITHM,
        api_settings.SIGNING_KEY,
        api_settings.VERIFYING_KEY,
        api_settings.AUDIENCE,
        api_settings.ISSUER,
        api_settings.JWK_URL,
        api_settings.LEEWAY,
        api_settings.JSON_ENCODER,
        legacy_signing_key=legacy_key,
    )
