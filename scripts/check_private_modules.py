#!/usr/bin/env python3
"""Fail on imports of private backend modules from outside their package, or of private symbols from another module."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
SKIP_DIRS = frozenset({".venv", "node_modules", "__pycache__"})
MODULE_EXEMPT_DIRS = frozenset({"tests"})


def _module_parts(path: Path) -> list[str]:
    parts = list(path.relative_to(BACKEND).with_suffix("").parts)
    return parts[:-1] if parts[-1] == "__init__" else parts


def _package_parts(path: Path) -> list[str]:
    parts = _module_parts(path)
    return parts if path.name == "__init__.py" else parts[:-1]


def _is_local_module(parts: list[str]) -> bool:
    base = BACKEND.joinpath(*parts)
    return base.with_suffix(".py").is_file() or (base / "__init__.py").is_file()


def _is_backend_module(module: list[str]) -> bool:
    return bool(module) and (BACKEND / module[0]).is_dir()


def _is_private(segment: str) -> bool:
    return segment.startswith("_") and not segment.startswith("__")


def _iter_python_files() -> Iterator[Path]:
    for path in sorted(BACKEND.rglob("*.py")):
        if not SKIP_DIRS.intersection(path.relative_to(BACKEND).parts[:-1]):
            yield path


def _is_module_exempt(path: Path) -> bool:
    return bool(MODULE_EXEMPT_DIRS.intersection(path.relative_to(BACKEND).parts[:-1]))


def _from_module(node: ast.ImportFrom, path: Path) -> list[str]:
    if node.level:
        package = _package_parts(path)
        base = package[: len(package) - (node.level - 1)]
    else:
        base = []
    return base + (node.module.split(".") if node.module else [])


def _imported_modules(node: ast.Import | ast.ImportFrom, path: Path) -> list[list[str]]:
    """Absolute module paths an import statement pulls in.
    param node(ast.Import | ast.ImportFrom): the import statement
    param path(Path): file containing the import
    return(list[list[str]]): module paths as segment lists
    """
    if isinstance(node, ast.Import):
        return [alias.name.split(".") for alias in node.names]
    module = _from_module(node, path)
    found = [module] if module else []
    # `from pkg import name` imports a module only when `name` is a submodule, not a symbol.
    found += [module + [a.name] for a in node.names if _is_local_module(module + [a.name])]
    return found


def _private_symbols(node: ast.ImportFrom, path: Path) -> list[str]:
    module = _from_module(node, path)
    if not _is_backend_module(module):
        return []
    return [
        ".".join(module + [a.name])
        for a in node.names
        if _is_private(a.name) and not _is_local_module(module + [a.name])
    ]


def _violation(importer: list[str], module: list[str]) -> str | None:
    if not _is_backend_module(module):
        return None
    for i, segment in enumerate(module):
        parent = module[:i]
        if _is_private(segment) and importer[:i] != parent:
            return (
                f"imports private module {'.'.join(module[: i + 1])} "
                f"from outside {'.'.join(parent) or '<root>'}"
            )
    return None


def _check_file(path: Path) -> tuple[list[str], list[tuple[int, str]]]:
    """Scan one file's imports.
    param path(Path): file to scan
    return(tuple[list[str], list[tuple[int, str]]]): private-module problems, (lineno, symbol) private-symbol imports
    """
    importer = _module_parts(path)
    problems: list[str] = []
    symbols: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if not _is_module_exempt(path):
            problems += [f"{node.lineno}: {m}" for m in _module_violations(importer, node, path)]
        if isinstance(node, ast.ImportFrom):
            symbols += [(node.lineno, s) for s in _private_symbols(node, path)]
    return problems, symbols


def _module_violations(
    importer: list[str], node: ast.Import | ast.ImportFrom, path: Path
) -> list[str]:
    modules = _imported_modules(node, path)
    return [m for m in (_violation(importer, module) for module in modules) if m]


def main() -> int:
    problems: list[str] = []
    for path in _iter_python_files():
        rel = str(path.relative_to(REPO_ROOT))
        module_problems, symbols = _check_file(path)
        problems += [f"{rel}:{p}" for p in module_problems]
        problems += [f"{rel}:{n}: imports private symbol {s}" for n, s in symbols]
    for line in problems:
        print(line)
    if problems:
        print("drop the underscore from a symbol or module that other modules import")
    return 1 if problems else 0

if __name__ == "__main__":
    raise SystemExit(main())
