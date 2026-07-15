import json
import re
import sys
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _ROOT / "pyproject.toml"
_PACKAGE_JSON = _ROOT / "frontend" / "package.json"


def set_pyproject_version(path: Path, version: str) -> None:
    """Rewrite [project].version, leaving every other table untouched.
    param path(Path): path to pyproject.toml
    param version(str): new semver string, e.g. "1.2.3"
    """
    text = path.read_text()
    current = tomllib.loads(text).get("project", {}).get("version")
    if current is None:
        raise ValueError(f"no [project].version in {path}")
    # Scope by the known value; a replacement function inserts `version` literally
    # so a value with regex-replacement syntax (\g<1>, \1) can't corrupt the output.
    line = re.compile(rf"""(?m)^(version\s*=\s*)(["']){re.escape(current)}\2""")
    new_text, count = line.subn(lambda m: f'{m.group(1)}"{version}"', text)
    if count != 1:
        raise ValueError(
            f"expected exactly one version = {current!r} line in {path}, found {count}"
        )
    path.write_text(new_text)


def set_package_json_version(path: Path, version: str) -> None:
    """Rewrite the top-level "version" field, preserving 2-space indent + trailing newline.
    param path(Path): path to package.json
    param version(str): new semver string
    """
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main(version: str) -> None:
    set_pyproject_version(_PYPROJECT, version)
    set_package_json_version(_PACKAGE_JSON, version)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: set_release_version.py <version>")
    main(sys.argv[1])
