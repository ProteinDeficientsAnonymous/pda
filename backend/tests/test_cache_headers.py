import pytest
from django.test import Client, override_settings


@pytest.fixture
def flutter_template_dir(tmp_path):
    """Create a minimal flutter/index.html template for the catch-all view."""
    template_dir = tmp_path / "templates"
    flutter_dir = template_dir / "flutter"
    flutter_dir.mkdir(parents=True)
    (flutter_dir / "index.html").write_text("<html><body>test</body></html>")
    return str(template_dir)


@pytest.mark.unit
class TestSPACacheHeaders:
    def test_spa_catchall_sets_no_cache_header(self, flutter_template_dir):
        """index.html responses must include Cache-Control: no-cache to prevent stale deploys."""
        with override_settings(
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [flutter_template_dir],
                    "APP_DIRS": True,
                    "OPTIONS": {"context_processors": []},
                }
            ]
        ):
            client = Client()
            response = client.get("/")
            assert response.status_code == 200
            assert response["Cache-Control"] == "no-cache"
