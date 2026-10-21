"""Dump the NinjaAPI OpenAPI schema to a JSON file for frontend codegen.

Mirrors ``dump_validation_codes``: writes ``backend/openapi_schema.json``,
which the frontend's ``types:api`` script reads to regenerate
``frontend/src/api/types.gen.ts``. Having the schema on disk lets CI run
``--check`` without a live Django server.

Run via ``make dump-openapi`` (wrapped by ``make frontend-types``).
"""

import json
from pathlib import Path

from config.urls import api
from django.core.management.base import BaseCommand

OUTPUT_PATH = Path(__file__).resolve().parents[3] / "openapi_schema.json"


class Command(BaseCommand):
    help = "Dump the NinjaAPI OpenAPI schema to openapi_schema.json."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit non-zero if the on-disk JSON is out of date.",
        )

    def handle(self, *args, check: bool = False, **options) -> None:
        schema = api.get_openapi_schema()
        serialized = json.dumps(schema, indent=2, sort_keys=True) + "\n"

        if check:
            existing = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
            if existing != serialized:
                self.stderr.write("openapi_schema.json is out of date — run `make dump-openapi`.")
                raise SystemExit(1)
            self.stdout.write("openapi_schema.json is up to date.")
            return

        OUTPUT_PATH.write_text(serialized)
        self.stdout.write(f"wrote {OUTPUT_PATH.relative_to(Path.cwd())}")
