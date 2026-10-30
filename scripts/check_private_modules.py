#!/usr/bin/env python3
"""Fail when a `_`-prefixed backend module is imported from outside its parent package (tests exempt)."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
SKIP_DIRS = frozenset({"tests", ".venv", "node_modules", "__pycache__"})


def _module_parts(path: Path) -> list[str]:
    parts = list(path.relative_to(BACKEND).with_suffix("").parts)
    return parts[:-1] if parts[-1] == "__init__" else parts


def _package_parts(path: Path) -> list[str]:
    parts = _module_parts(path)
    return parts if path.name == "__init__.py" else parts[:-1]


def _is_local_module(parts: list[str]) -> bool:
    base = BACKEND.joinpath(*parts)
    return base.with_suffix(".py").is_file() or (base / "__init__.py").is_file()


def _is_private(segment: str) -> bool:
    return segment.startswith("_") and not segment.startswith("__")


def _iter_python_files() -> Iterator[Path]:
    for path in sorted(BACKEND.rglob("*.py")):
        if not SKIP_DIRS.intersection(path.relative_to(BACKEND).parts[:-1]):
            yield path


def _imported_modules(node: ast.Import | ast.ImportFrom, path: Path) -> list[list[str]]:
    """Absolute module paths an import statement pulls in.
    param node(ast.Import | ast.ImportFrom): the import statement
    param path(Path): file containing the import
    return(list[list[str]]): module paths as segment lists
    """
    if isinstance(node, ast.Import):
        return [alias.name.split(".") for alias in node.names]
    if node.level:
        package = _package_parts(path)
        base = package[: len(package) - (node.level - 1)]
    else:
        base = []
    module = base + (node.module.split(".") if node.module else [])
    found = [module] if module else []
    # `from pkg import name` imports a module only when `name` is a submodule, not a symbol.
    found += [module + [a.name] for a in node.names if _is_local_module(module + [a.name])]
    return found


def _violation(importer: list[str], module: list[str]) -> str | None:
    if not module or not (BACKEND / module[0]).is_dir():
        return None
    for i, segment in enumerate(module):
        parent = module[:i]
        if _is_private(segment) and importer[:i] != parent:
            return (
                f"imports private module {'.'.join(module[: i + 1])} "
                f"from outside {'.'.join(parent) or '<root>'}"
            )
    return None


def main() -> int:
    problems: list[str] = []
    for path in _iter_python_files():
        importer = _module_parts(path)
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for module in _imported_modules(node, path):
                if message := _violation(importer, module):
                    rel = path.relative_to(REPO_ROOT)
                    problems.append(f"{rel}:{node.lineno}: {message}")
    for line in problems:
        print(line)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
