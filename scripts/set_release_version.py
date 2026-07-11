import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _ROOT / "pyproject.toml"
_PACKAGE_JSON = _ROOT / "frontend" / "package.json"


def set_pyproject_version(path: Path, version: str) -> None:
    """Rewrite the [project].version line only.
    param path(Path): path to pyproject.toml
    param version(str): new semver string, e.g. "1.2.3"
    """
    text = path.read_text()
    # Match the first `version = "..."` that sits under [project]: it is the
    # first version assignment in the file, before any [tool.*] table.
    pattern = re.compile(r'(?m)^(version\s*=\s*")[^"]*(")')
    new_text, count = pattern.subn(rf'\g<1>{version}\g<2>', text, count=1)
    if count != 1:
        raise ValueError(f"expected exactly one [project].version line in {path}")
    path.write_text(new_text)


def set_package_json_version(path: Path, version: str) -> None:
    """Rewrite the top-level "version" field, preserving 2-space indent + trailing newline.
    param path(Path): path to package.json
    param version(str): new semver string
    """
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")


def main(version: str) -> None:
    set_pyproject_version(_PYPROJECT, version)
    set_package_json_version(_PACKAGE_JSON, version)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: set_release_version.py <version>")
    main(sys.argv[1])
