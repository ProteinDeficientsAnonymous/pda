import importlib
import warnings
from unittest import mock

import jwt
import pytest
from config.jwt_backend import LegacyKeyTokenBackend, install_legacy_key_backend
from jwt.warnings import InsecureKeyLengthWarning
from ninja_jwt import state
from ninja_jwt.backends import TokenBackend
from ninja_jwt.exceptions import TokenBackendError, TokenError
from ninja_jwt.tokens import RefreshToken

NEW_KEY = "n" * 32
LEGACY_KEY = "l" * 20


@pytest.fixture
def reload_settings(monkeypatch):
    import config.settings as settings_module

    yield lambda: importlib.reload(settings_module)
    monkeypatch.undo()
    importlib.reload(settings_module)


@pytest.mark.unit
class TestJwtSigningKeySettings:
    def test_unset_falls_back_to_secret_key(self, monkeypatch, reload_settings):
        monkeypatch.setenv("SECRET_KEY", LEGACY_KEY)
        monkeypatch.delenv("JWT_SIGNING_KEY", raising=False)
        s = reload_settings()
        assert s.NINJA_JWT["SIGNING_KEY"] == LEGACY_KEY
        assert s.JWT_LEGACY_VERIFYING_KEY is None

    def test_set_signs_with_new_key_and_keeps_secret_key_for_verify(
        self, monkeypatch, reload_settings
    ):
        monkeypatch.setenv("SECRET_KEY", LEGACY_KEY)
        monkeypatch.setenv("JWT_SIGNING_KEY", NEW_KEY)
        s = reload_settings()
        assert s.NINJA_JWT["SIGNING_KEY"] == NEW_KEY
        assert s.JWT_LEGACY_VERIFYING_KEY == LEGACY_KEY

    def test_short_key_rejected(self, monkeypatch, reload_settings):
        monkeypatch.setenv("JWT_SIGNING_KEY", "x" * 31)
        with pytest.raises(ValueError, match="JWT_SIGNING_KEY"):
            reload_settings()


def _backend() -> LegacyKeyTokenBackend:
    return LegacyKeyTokenBackend("HS256", NEW_KEY, legacy_signing_key=LEGACY_KEY)


def _sign(key: str, **claims) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InsecureKeyLengthWarning)
        return jwt.encode({"user_id": "u1", **claims}, key, algorithm="HS256")


@pytest.mark.unit
class TestLegacyKeyTokenBackend:
    def test_new_key_token_decodes(self):
        assert _backend().decode(_sign(NEW_KEY))["user_id"] == "u1"

    def test_legacy_key_token_decodes_without_key_length_warning(self):
        token = _sign(LEGACY_KEY)
        with warnings.catch_warnings():
            warnings.simplefilter("error", InsecureKeyLengthWarning)
            assert _backend().decode(token)["user_id"] == "u1"

    def test_unknown_key_rejected(self):
        with pytest.raises(TokenBackendError):
            _backend().decode(_sign("z" * 32))

    def test_expired_new_key_token_not_retried_with_legacy(self):
        backend = _backend()
        with mock.patch.object(backend.legacy, "decode") as legacy_decode:
            with pytest.raises(TokenBackendError):
                backend.decode(_sign(NEW_KEY, exp=1))
        legacy_decode.assert_not_called()

    def test_encode_uses_new_key(self):
        token = _backend().encode({"user_id": "u1"})
        assert jwt.decode(token, NEW_KEY, algorithms=["HS256"])["user_id"] == "u1"


@pytest.mark.django_db
class TestInstallLegacyKeyBackend:
    def test_noop_without_legacy_key(self, monkeypatch, settings):
        settings.JWT_LEGACY_VERIFYING_KEY = None
        original = TokenBackend("HS256", NEW_KEY)
        monkeypatch.setattr(state, "token_backend", original)
        install_legacy_key_backend()
        assert state.token_backend is original

    def test_refresh_token_signed_with_legacy_key_still_valid(self, monkeypatch, test_user):
        monkeypatch.setattr(state, "token_backend", TokenBackend("HS256", LEGACY_KEY))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InsecureKeyLengthWarning)
            old_token = str(RefreshToken.for_user(test_user))

        monkeypatch.setattr(state, "token_backend", _backend())
        assert RefreshToken(old_token)["user_id"] == str(test_user.id)

    def test_refresh_token_with_unknown_key_rejected(self, monkeypatch, test_user):
        monkeypatch.setattr(state, "token_backend", TokenBackend("HS256", "z" * 32))
        forged = str(RefreshToken.for_user(test_user))

        monkeypatch.setattr(state, "token_backend", _backend())
        with pytest.raises(TokenError):
            RefreshToken(forged)
