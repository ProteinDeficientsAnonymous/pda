import json
import re
import sys
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _ROOT / "pyproject.toml"
_PACKAGE_JSON = _ROOT / "frontend" / "package.json"


def set_pyproject_version(path: Path, version: str) -> None:
    """Rewrite the version under [project], leaving every other table untouched.
    param path(Path): path to pyproject.toml
    param version(str): new semver string, e.g. "1.2.3"
    """
    text = path.read_text()
    if "version" not in tomllib.loads(text).get("project", {}):
        raise ValueError(f"no [project].version in {path}")
    # Replace `version = "..."` only within the [project] table: scan from the
    # [project] header to the next top-level table header.
    project = re.compile(r"(?ms)^\[project\]\s*$.*?(?=^\[|\Z)")
    version_line = re.compile(r'(?m)^(version\s*=\s*")[^"]*(")')

    def bump(block: re.Match[str]) -> str:
        new_block, count = version_line.subn(rf"\g<1>{version}\g<2>", block.group(0), count=1)
        if count != 1:
            raise ValueError(f"expected exactly one [project].version line in {path}")
        return new_block

    path.write_text(project.sub(bump, text, count=1))


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
