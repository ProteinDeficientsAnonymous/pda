import importlib.util
import json
import tomllib
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


def test_pyproject_version_scoped_to_project_table_even_when_tool_table_is_first(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text(
        '[tool.foo]\nversion = "should-not-touch"\n\n[project]\nname = "pda"\nversion = "0.1.0"\n'
    )
    srv.set_pyproject_version(p, "1.2.3")
    out = p.read_text()
    assert 'version = "1.2.3"' in out
    assert out.count('version = "1.2.3"') == 1
    assert 'version = "should-not-touch"' in out  # [tool.foo] before [project] untouched


def test_package_json_preserves_trailing_newline(tmp_path):
    p = tmp_path / "package.json"
    p.write_text(json.dumps({"name": "frontend", "version": "0.0.0"}, indent=2) + "\n")
    srv.set_package_json_version(p, "9.9.9")
    assert p.read_text().endswith("\n")


def test_pyproject_version_handles_single_quotes_and_no_spaces(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text("[project]\nname = 'pda'\nversion='0.1.0'\n")
    srv.set_pyproject_version(p, "1.2.3")
    assert tomllib.loads(p.read_text())["project"]["version"] == "1.2.3"


def test_pyproject_version_inserts_literally_not_as_regex_template(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text('[project]\nversion = "0.1.0"\n')
    # a value containing regex-replacement syntax must land in the file verbatim,
    # not be expanded by re.sub (which would corrupt the line)
    srv.set_pyproject_version(p, r"9.9.9\g<1>x")
    assert r'version = "9.9.9\g<1>x"' in p.read_text()


def test_pyproject_version_updates_project_when_another_table_shares_the_value(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text(
        "[project]\n"
        'version = "0.1.0"\n'
        "\n"
        "[tool.foo]\n"
        'version = "0.1.0"\n'  # same value as [project], different table → left alone
    )
    srv.set_pyproject_version(p, "1.2.3")
    out = p.read_text()
    assert tomllib.loads(out)["project"]["version"] == "1.2.3"
    assert tomllib.loads(out)["tool"]["foo"]["version"] == "0.1.0"


def test_package_json_preserves_non_ascii(tmp_path):
    p = tmp_path / "package.json"
    p.write_text(
        json.dumps({"author": "José", "version": "0.0.0"}, indent=2, ensure_ascii=False) + "\n"
    )
    srv.set_package_json_version(p, "1.2.3")
    out = p.read_text()
    assert "José" in out  # not escaped to é
    assert json.loads(out)["version"] == "1.2.3"
