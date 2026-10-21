"""The Visual baseline is the nearest ancestor that actually uploaded screenshots.

Release commits are `[skip ci]`, so the PR merge-base often has no Visual run.
reg-actions then reports every screenshot as new.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load():
    path = Path(__file__).resolve().parents[2] / "scripts" / "screenshot_baseline.py"
    spec = importlib.util.spec_from_file_location("screenshot_baseline", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pick_baseline_sha_merge_base_has_run_returns_merge_base():
    baseline = _load()
    ran = {"merge-base"}

    assert baseline.pick_baseline_sha(["merge-base", "older"], ran.__contains__) == "merge-base"


def test_pick_baseline_sha_merge_base_lacks_run_returns_closest_ancestor():
    baseline = _load()
    ran = {"parent", "older"}

    assert baseline.pick_baseline_sha(["skip-ci", "parent", "older"], ran.__contains__) == "parent"


def test_pick_baseline_sha_no_run_in_ancestors_returns_none():
    baseline = _load()

    assert baseline.pick_baseline_sha(["skip-ci", "also-skipped"], set().__contains__) is None


def test_baseline_pair_stack_pr_diffs_against_main_not_the_parent_branch():
    baseline = _load()

    assert baseline.baseline_pair("main-tip", "feature-a-tip", "feature-b") == (
        "main-tip",
        "feature-b",
    )
