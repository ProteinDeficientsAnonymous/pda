import importlib.util
import json
import subprocess
import sys

import pytest

from tests._paths import REPO_ROOT

HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "post-push-ci-reminder.py"


@pytest.fixture
def hook():
    spec = importlib.util.spec_from_file_location("post_push_ci_reminder", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feat-x"], cwd=root, check=True)
    return root


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("git push", "."),
        ("git push -u origin feat-x", "."),
        ("git commit -qm 'x' && git push", "."),
        ("cd sub && git push", "sub"),
        ('cd "my dir" && git push', "my dir"),
        ("git -C sub push", "sub"),
        ("gh pr create --draft --base main", "."),
        ("git status", None),
        ("git pushy", None),
        ("git push origin --delete old-branch", None),
        ("git push origin :old-branch", None),
        ("git commit -m 'docs: explain git push flow'", None),
        ("echo git push later", None),
        ("gh pr create -d --base main", "."),
        ("git push origin feat; git branch -d old", "."),
        ("git push origin feat || git branch -d old", "."),
        ("git -c push.default=current push", "."),
        ("git --no-pager push", "."),
        ("FOO=1 git push", "."),
        ("(cd sub && git push)", "sub"),
    ],
)
def test_push_dir(hook, tmp_path, command, expected):
    result = hook.push_dir(command, tmp_path)
    assert result == (None if expected is None else (tmp_path / expected).resolve())


def _run_main(hook, monkeypatch, capsys, event: dict) -> tuple[int, str]:
    payload = json.dumps(event)
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: payload})())
    code = hook.main()
    return code, capsys.readouterr().out


@pytest.mark.unit
def test_non_push_commands_emit_nothing(hook, repo, monkeypatch, capsys):
    event = {"cwd": str(repo), "tool_input": {"command": "git status"}}
    assert _run_main(hook, monkeypatch, capsys, event) == (0, "")


@pytest.fixture
def open_pr(hook, monkeypatch):
    monkeypatch.setattr(hook, "has_open_pr", lambda where: True)


@pytest.fixture
def no_open_pr(hook, monkeypatch):
    monkeypatch.setattr(hook, "has_open_pr", lambda where: False)


@pytest.mark.unit
def test_push_with_open_pr_emits_ci_reminder(hook, repo, monkeypatch, capsys, open_pr):
    event = {"cwd": str(repo), "tool_input": {"command": "git push -u origin feat-x"}}
    code, out = _run_main(hook, monkeypatch, capsys, event)
    assert code == 0
    specific = json.loads(out)["hookSpecificOutput"]
    assert specific["hookEventName"] == "PostToolUse"
    assert "`feat-x`" in specific["additionalContext"]
    assert "fix any failure" in specific["additionalContext"]


@pytest.mark.unit
def test_push_without_pr_emits_nothing(hook, repo, monkeypatch, capsys, no_open_pr):
    event = {"cwd": str(repo), "tool_input": {"command": "git push -u origin feat-x"}}
    assert _run_main(hook, monkeypatch, capsys, event) == (0, "")


@pytest.mark.unit
def test_pr_creation_reminds_without_checking_gh(hook, tmp_path, no_open_pr):
    assert hook.ci_runs("git push -u origin feat-x && gh pr create --fill", tmp_path) is True


@pytest.mark.unit
def test_missing_push_dir_skips_pr_lookup(hook, tmp_path, open_pr):
    assert hook.ci_runs("git push", tmp_path / "missing") is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [(0, "OPEN\n", True), (0, "MERGED\n", False), (1, "", False)],
)
def test_has_open_pr_reads_gh_state(hook, tmp_path, monkeypatch, returncode, stdout, expected):
    done = subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")
    monkeypatch.setattr(hook.subprocess, "run", lambda *a, **k: done)
    assert hook.has_open_pr(tmp_path) is expected


@pytest.mark.unit
@pytest.mark.parametrize("error", [OSError("no gh"), subprocess.TimeoutExpired("gh", 10)])
def test_has_open_pr_tolerates_missing_or_slow_gh(hook, tmp_path, monkeypatch, error):
    def boom(*args, **kwargs):
        raise error

    monkeypatch.setattr(hook.subprocess, "run", boom)
    assert hook.has_open_pr(tmp_path) is False


@pytest.mark.unit
def test_reminder_without_a_branch_still_reads(hook, tmp_path):
    assert "You pushed this branch;" in hook.reminder(hook.current_branch(tmp_path / "missing"))


@pytest.mark.unit
def test_invalid_stdin_is_ignored(hook, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", type("S", (), {"read": lambda self: "not json"})())
    assert hook.main() == 0
    assert capsys.readouterr().out == ""
