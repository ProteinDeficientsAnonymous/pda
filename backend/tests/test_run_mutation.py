import configparser
import importlib.util
import subprocess
import sys

import pytest

from tests._paths import REPO_ROOT

SCRIPT_PATH = REPO_ROOT / "scripts" / "run_mutation.py"


@pytest.fixture
def mod(monkeypatch):
    spec = importlib.util.spec_from_file_location("run_mutation", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return module


@pytest.fixture
def backend(tmp_path):
    root = tmp_path / "backend"
    for pkg in ("community", "users", "tests", "mutants"):
        (root / pkg).mkdir(parents=True)
        (root / pkg / "__init__.py").write_text("")
    (root / "templates").mkdir()
    (root / "openapi_schema.json").write_text("{}")
    return root


def _done(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


def _builds_template(mod, cmd: list[str]) -> bool:
    return cmd[-1] == mod.MUTATION_DB_TEMPLATE


@pytest.mark.unit
def test_changed_backend_files_skips_tests_and_migrations(mod, monkeypatch):
    out = "backend/community/views.py\nbackend/tests/test_x.py\nbackend/users/migrations/0001.py\nbackend/a.txt\n"
    monkeypatch.setattr(mod.subprocess, "check_output", lambda *a, **k: out)
    assert mod.changed_backend_files("origin/main") == ["community/views.py"]


@pytest.mark.unit
def test_changed_backend_files_skips_management_commands_and_seed_data(mod, monkeypatch):
    out = (
        "backend/community/views.py\n"
        "backend/community/management/commands/seed_staging.py\n"
        "backend/community/management/commands/_seed_staging_data.py\n"
        "backend/community/dev_tools/_seed_extra.py\n"
        "backend/community/seeding.py\n"
    )
    monkeypatch.setattr(mod.subprocess, "check_output", lambda *a, **k: out)
    assert mod.changed_backend_files("origin/main") == ["community/views.py"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("listed", "expected"),
    [
        ("tests/test_a.py\ntests/test_b.py\n", ["tests/test_a.py", "tests/test_b.py"]),
        ("__FULL__\n", None),
        ("", None),
    ],
)
def test_affected_tests_has_no_list_for_the_full_suite(mod, monkeypatch, listed, expected):
    monkeypatch.setattr(mod.subprocess, "check_output", lambda *a, **k: listed)
    assert mod.affected_tests("origin/main") == expected


@pytest.mark.unit
def test_render_config_scopes_mutation_to_the_diff(mod, backend):
    text = mod.render_config(backend, ["users/_transitions.py"], ["tests/users/test_x.py"])
    assert text.startswith(mod.CONFIG_MARKER)
    parser = configparser.ConfigParser()
    parser.read_string(text)
    section = parser["mutmut"]
    assert section["process_isolation"] == "forkserver"
    assert section["log_to_file"] == "true"
    assert section["source_paths"].split() == ["community/", "users/"]
    assert section["only_mutate"].split() == ["users/_transitions.py"]
    assert section["also_copy"].split() == ["templates/", "manage.py", "openapi_schema.json"]
    assert "--hypothesis-seed=0" in section["pytest_add_cli_args"].split()
    assert section["pytest_add_cli_args_test_selection"].split() == ["tests/users/test_x.py"]


@pytest.mark.unit
def test_survivor_ids_parses_mutmut_results(mod):
    text = "    users._t.x_a__mutmut_3: survived\n    users._t.x_a__mutmut_4: killed\n    users._t.x_b__mutmut_1: survived\n"
    assert mod.survivor_ids(text) == ["users._t.x_a__mutmut_3", "users._t.x_b__mutmut_1"]


@pytest.mark.unit
def test_no_changed_files_skips_mutation(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "changed_backend_files", lambda base: [])
    assert mod.main([]) == 0
    assert "No changed backend domain files" in capsys.readouterr().out


@pytest.mark.unit
def test_run_mutmut_writes_then_removes_config_and_collects_diffs(mod, monkeypatch, backend):
    monkeypatch.setattr(mod, "BACKEND", backend)
    monkeypatch.setattr(mod, "CONFIG", backend / "setup.cfg")
    seen_config: list[bool] = []

    def fake_mutmut(*args):
        seen_config.append((backend / "setup.cfg").exists())
        if args[0] == "results":
            return _done("    users.x__mutmut_1: survived\n")
        return _done(f"diff of {args[1]}")

    monkeypatch.setattr(mod, "_mutmut", fake_mutmut)
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **k: _done(""))
    survivors, diffs = mod.run_mutmut(["users/a.py"], ["tests/"])
    assert survivors == ["users.x__mutmut_1"]
    assert diffs == {"users.x__mutmut_1": "diff of users.x__mutmut_1"}
    assert seen_config == [True, True]
    assert not (backend / "setup.cfg").exists()
    assert not (backend / "mutants").exists()


@pytest.mark.unit
def test_failed_mutmut_run_fails_the_step_instead_of_passing(mod, monkeypatch, backend, capsys):
    monkeypatch.setattr(mod, "BACKEND", backend)
    monkeypatch.setattr(mod, "CONFIG", backend / "setup.cfg")
    monkeypatch.setattr(
        mod.subprocess,
        "run",
        lambda cmd, **k: subprocess.CompletedProcess(cmd, 0 if _builds_template(mod, cmd) else 1),
    )
    monkeypatch.setattr(mod, "_mutmut", lambda *a: pytest.fail("results must not be read"))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert mod.main(["users/a.py", "--tests", "tests/"]) == 1
    out = capsys.readouterr().out
    assert "could not run" in out
    assert "no surviving mutants" not in out
    assert "::error::" in out
    assert not (backend / "setup.cfg").exists()


@pytest.mark.unit
def test_full_suite_diff_skips_mutation_with_a_notice(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "changed_backend_files", lambda base: ["community/views.py"])
    monkeypatch.setattr(mod, "affected_tests", lambda base: None)
    monkeypatch.setattr(mod, "run_mutmut", lambda *a: pytest.fail("must not mutate"))
    assert mod.main(["--enforce"]) == 0
    assert "Mutation testing: skipped" in capsys.readouterr().out


@pytest.mark.unit
def test_failed_baseline_is_rerun_unmutated_and_its_failures_shown(
    mod, monkeypatch, backend, capsys
):
    monkeypatch.setattr(mod, "BACKEND", backend)
    monkeypatch.setattr(mod, "CONFIG", backend / "setup.cfg")
    calls: list[tuple[list[str], dict]] = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if _builds_template(mod, cmd):
            return _done("built\n")
        if cmd[-1] == "run":
            (backend / "mutants").mkdir()
            return subprocess.CompletedProcess(cmd, 1)
        return subprocess.CompletedProcess(
            cmd, 1, stdout="FAILED tests/test_x.py::test_y\n", stderr=""
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod.main(["users/a.py", "--tests", "tests/test_x.py"]) == 1
    out = capsys.readouterr().out
    assert "FAILED tests/test_x.py::test_y" in out
    rerun, kwargs = calls[-1]
    assert rerun[-1] == "tests/test_x.py"
    assert "addopts=" in rerun
    assert kwargs["cwd"] == backend / "mutants"
    assert kwargs["env"]["MUTANT_UNDER_TEST"] == ""
    assert kwargs["env"]["PDA_MUTATION_DB_TEMPLATE"] == mod.MUTATION_DB_TEMPLATE
    assert not (backend / "mutants").exists()


@pytest.mark.unit
def test_run_mutmut_refuses_to_overwrite_a_hand_written_config(mod, monkeypatch, backend):
    monkeypatch.setattr(mod, "BACKEND", backend)
    monkeypatch.setattr(mod, "CONFIG", backend / "setup.cfg")
    (backend / "setup.cfg").write_text("[flake8]\n")
    with pytest.raises(SystemExit, match="not overwriting"):
        mod.run_mutmut(["users/a.py"], ["tests/"])
    assert (backend / "setup.cfg").read_text() == "[flake8]\n"


@pytest.mark.unit
def test_survivors_are_reported_and_fail_only_when_enforced(mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        mod, "run_mutmut", lambda targets, tests: (["m3", "m7"], {"m3": "-a\n+b", "m7": "-c\n+d"})
    )
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert mod.main(["community/views.py", "--tests", "tests/test_views.py"]) == 0
    assert mod.main(["community/views.py", "--tests", "tests/test_views.py", "--enforce"]) == 1
    out = capsys.readouterr().out
    assert "2 surviving mutant(s)" in out
    assert "-c\n+d" in out
    assert "skips decorated functions" in out
    assert "2 surviving mutant(s)" in summary.read_text()


@pytest.mark.unit
def test_report_truncates_long_survivor_lists(mod):
    names = [str(i) for i in range(mod.MAX_SHOWN + 5)]
    text = mod.report(names, {})
    assert "…and 5 more" in text
    assert text.count("```diff") == mod.MAX_SHOWN


@pytest.mark.unit
def test_no_survivors_passes_when_enforced(mod, monkeypatch, capsys):
    monkeypatch.setattr(mod, "run_mutmut", lambda targets, tests: ([], {}))
    assert mod.main(["community/views.py", "--tests", "tests/", "--enforce"]) == 0
    out = capsys.readouterr().out
    assert "no surviving mutants" in out
    assert "skips decorated functions" in out


@pytest.mark.unit
def test_postgres_mutants_clone_a_premigrated_template(mod, monkeypatch, backend):
    monkeypatch.setattr(mod, "BACKEND", backend)
    monkeypatch.setattr(mod, "CONFIG", backend / "setup.cfg")
    monkeypatch.setattr(mod, "_mutmut", lambda *a: _done(""))
    envs: list[dict] = []

    def fake_run(cmd, **kwargs):
        if _builds_template(mod, cmd):
            assert kwargs["env"]["DJANGO_SETTINGS_MODULE"] == "config.settings"
            return _done("built\n")
        envs.append(kwargs["env"])
        return _done("")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    mod.run_mutmut(["users/a.py"], ["tests/"])
    assert [e["PDA_MUTATION_DB_TEMPLATE"] for e in envs] == [mod.MUTATION_DB_TEMPLATE]


@pytest.mark.unit
def test_non_postgres_mutants_run_without_a_template(mod, monkeypatch, backend):
    monkeypatch.delenv("PDA_MUTATION_DB_TEMPLATE", raising=False)
    monkeypatch.setattr(mod, "BACKEND", backend)
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **k: _done(""))
    assert "PDA_MUTATION_DB_TEMPLATE" not in mod.mutation_env()


@pytest.mark.unit
def test_failed_template_build_reports_instead_of_mutating(mod, monkeypatch, backend, capsys):
    monkeypatch.setattr(mod, "BACKEND", backend)
    monkeypatch.setattr(mod, "CONFIG", backend / "setup.cfg")

    def fake_run(cmd, **kwargs):
        assert _builds_template(mod, cmd), "mutmut must not start"
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="migration 0042 broke\n")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    assert mod.main(["users/a.py", "--tests", "tests/"]) == 1
    out = capsys.readouterr().out
    assert "migrating the template test database failed" in out
    assert "migration 0042 broke" in out
    assert not (backend / "setup.cfg").exists()
