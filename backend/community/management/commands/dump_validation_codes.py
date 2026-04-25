"""Dump the Code catalog to a JSON file for frontend codegen.

Reads ``community/_validation.py`` via AST (not import) so we can pick up the
``# params: { ... }`` annotations that sit next to each code constant, then
writes ``community/validation_codes.json``. The frontend generator consumes
that file to produce ``validationCodes.gen.ts``.

Run via ``make dump-codes`` (wrapped by ``make frontend-types``).
"""

import ast
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand

VALIDATION_MODULE = Path(__file__).resolve().parents[2] / "_validation.py"
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "validation_codes.json"

_PARAMS_COMMENT_RE = re.compile(r"#\s*params:\s*(\{[^}]*\})")


class Command(BaseCommand):
    help = "Dump Code catalog (and declared param keys) to validation_codes.json."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit non-zero if the on-disk JSON is out of date.",
        )

    def handle(self, *args, check: bool = False, **options) -> None:
        catalog = _extract_catalog(VALIDATION_MODULE)
        serialized = json.dumps(catalog, indent=2, sort_keys=False) + "\n"

        if check:
            existing = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
            if existing != serialized:
                self.stderr.write("validation_codes.json is out of date — run `make dump-codes`.")
                raise SystemExit(1)
            self.stdout.write("validation_codes.json is up to date.")
            return

        OUTPUT_PATH.write_text(serialized)
        self.stdout.write(f"wrote {OUTPUT_PATH.relative_to(Path.cwd())}")


def _extract_catalog(module_path: Path) -> dict:
    """Parse _validation.py and return ``{domain: [{name, value, params}]}``.

    AST parsing (rather than import + introspection) lets us capture the
    trailing ``# params: { ... }`` comments, which encode what keys the FE
    can expect for interpolation.
    """
    source = module_path.read_text()
    tree = ast.parse(source)
    source_lines = source.splitlines()

    code_class = _find_class(tree, "Code")
    if code_class is None:
        raise RuntimeError("Code class not found in _validation.py")

    domains: dict[str, list[dict]] = {}
    for domain_node in code_class.body:
        if not isinstance(domain_node, ast.ClassDef):
            continue
        constants = _extract_domain_constants(domain_node, source_lines)
        if constants:
            domains[domain_node.name] = constants

    return {"domains": domains}


def _extract_domain_constants(domain_node: ast.ClassDef, source_lines: list[str]) -> list[dict]:
    """Return every ``NAME = "value"  # params: ...`` constant on a Code.<Domain>."""
    constants: list[dict] = []
    for stmt in domain_node.body:
        entry = _parse_constant(stmt, source_lines)
        if entry is not None:
            constants.append(entry)
    return constants


def _find_class(tree: ast.Module, name: str) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _parse_constant(stmt: ast.stmt, source_lines: list[str]) -> dict | None:
    """Return ``{name, value, params}`` for a ``NAME = "value"  # params: { ... }`` line."""
    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
        return None
    target = stmt.targets[0]
    if not isinstance(target, ast.Name) or not isinstance(stmt.value, ast.Constant):
        return None
    if not isinstance(stmt.value.value, str):
        return None

    params_keys = _parse_params_comment(stmt, source_lines)
    return {
        "name": target.id,
        "value": stmt.value.value,
        "params": params_keys,
    }


def _parse_params_comment(stmt: ast.stmt, source_lines: list[str]) -> list[str]:
    """Extract keys from ``# params: { key1: type, key2: type }`` in the statement.

    Scans every line of the statement so multi-line parenthesized assignments
    (where the comment sits on an inner line) are handled. Returns an empty
    list when no comment is present.
    """
    end_line = getattr(stmt, "end_lineno", stmt.lineno) or stmt.lineno
    for line_no in range(stmt.lineno, end_line + 1):
        line = source_lines[line_no - 1]
        match = _PARAMS_COMMENT_RE.search(line)
        if match:
            break
    else:
        return []

    body = match.group(1).strip("{} ")
    if not body:
        return []
    keys: list[str] = []
    for part in body.split(","):
        key = part.split(":", 1)[0].strip()
        if key:
            keys.append(key)
    return keys
