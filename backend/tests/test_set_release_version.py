import importlib.util
import json
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "set_release_version.py"
_spec = importlib.util.spec_from_file_location("set_release_version", _SCRIPT)
srv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srv)


def test_set_pyproject_version_rewrites_only_version_line(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text(
        "[project]\n"
        'name = "pda"\n'
        'version = "0.1.0"\n'
        'description = "keep me"\n'
        "\n"
        "[tool.ruff]\n"
        'version = "should-not-touch"\n'
    )
    srv.set_pyproject_version(p, "1.2.3")
    out = p.read_text()
    assert 'version = "1.2.3"' in out
    assert out.count('version = "1.2.3"') == 1
    assert 'name = "pda"' in out
    assert 'description = "keep me"' in out
    assert 'version = "should-not-touch"' in out  # only [project].version changes


def test_set_package_json_version_rewrites_version(tmp_path):
    p = tmp_path / "package.json"
    p.write_text(
        json.dumps({"name": "frontend", "version": "0.0.0", "type": "module"}, indent=2) + "\n"
    )
    srv.set_package_json_version(p, "1.2.3")
    data = json.loads(p.read_text())
    assert data["version"] == "1.2.3"
    assert data["name"] == "frontend"
    assert data["type"] == "module"


def test_package_json_preserves_trailing_newline(tmp_path):
    p = tmp_path / "package.json"
    p.write_text(json.dumps({"name": "frontend", "version": "0.0.0"}, indent=2) + "\n")
    srv.set_package_json_version(p, "9.9.9")
    assert p.read_text().endswith("\n")
