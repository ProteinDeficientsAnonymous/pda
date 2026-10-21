#!/usr/bin/env python3
"""Choose the commit reg-actions should diff PR screenshots against.

The baseline artifact is the last successful Visual run on main. A pull
request into another branch still diffs against that, so a stack that is
squash-merged later still gets a comparison. Release commits skip CI, so the
merge-base with main often has no Visual run. Walk ancestors until a
successful Visual run on main exists.

ponytail: walks at most 30 ancestors. A longer stretch of commits with no
successful Visual run fails the job. Upgrade: paginate `gh run list` for the
workflow instead of walking commits.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable

MAX_ANCESTORS = 30


def baseline_pair(main_sha: str, pr_base_sha: str, head_sha: str) -> tuple[str, str]:
    """Diff every PR against main. Only a push to main uploads the baseline."""
    del pr_base_sha
    return main_sha, head_sha


def pick_baseline_sha(
    ancestor_shas: list[str],
    has_success: Callable[[str], bool],
) -> str | None:
    for sha in ancestor_shas:
        if has_success(sha):
            return sha
    return None


def _run(args: list[str]) -> str:
    return subprocess.check_output(args, text=True).strip()


def fetch_commits(pr_number: str) -> tuple[str, str]:
    fetch = ["git", "fetch", "--no-tags", "origin", "main"]
    if _run(["git", "rev-parse", "--is-shallow-repository"]) == "true":
        fetch.insert(2, "--unshallow")
    subprocess.run(fetch, check=True)
    # The next fetch replaces FETCH_HEAD, so keep main's SHA now.
    main_sha = _run(["git", "rev-parse", "FETCH_HEAD"])
    subprocess.run(
        ["git", "fetch", "--no-tags", "origin", f"pull/{pr_number}/head"],
        check=True,
    )
    return main_sha, _run(["git", "rev-parse", "FETCH_HEAD"])


def ancestors(sha: str, limit: int = MAX_ANCESTORS) -> list[str]:
    out = _run(["git", "rev-list", f"--max-count={limit}", sha])
    return [line for line in out.splitlines() if line]


def has_visual_success(sha: str) -> bool:
    raw = _run(
        [
            "gh",
            "run",
            "list",
            "--commit",
            sha,
            "--workflow",
            "visual.yml",
            "--branch",
            "main",
            "--status",
            "success",
            "--limit",
            "1",
            "--json",
            "databaseId",
        ]
    )
    return bool(json.loads(raw))


def write_sha(sha: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a") as fh:
            fh.write(f"sha={sha}\n")
    print(sha)


def main() -> None:
    pr_number = os.environ["PR_NUMBER"]
    main_sha, head_sha = fetch_commits(pr_number)
    left, right = baseline_pair(main_sha, os.environ.get("BASE_SHA", ""), head_sha)
    base = _run(["git", "merge-base", left, right])
    sha = pick_baseline_sha(ancestors(base), has_visual_success)
    if sha is None:
        sys.exit(f"No successful Visual run on main within {MAX_ANCESTORS} commits of {base}")
    print(f"screenshot baseline {sha} (merge-base {base})", file=sys.stderr)
    write_sha(sha)


if __name__ == "__main__":
    main()
