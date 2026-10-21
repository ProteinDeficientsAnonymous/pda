#!/usr/bin/env python3
"""Choose the commit reg-actions should diff PR screenshots against.

reg-actions looks up a GitHub Actions artifact whose workflow run head SHA is
the PR merge-base. Release commits use [skip ci], so that SHA has no Visual
run and every image is reported as new. Walk ancestors until a successful
Visual run on main exists.

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


def fetch_commits(pr_number: str) -> None:
    fetch = ["git", "fetch", "--no-tags", "origin", "main"]
    if _run(["git", "rev-parse", "--is-shallow-repository"]) == "true":
        fetch.insert(2, "--unshallow")
    subprocess.run(fetch, check=True)
    subprocess.run(
        ["git", "fetch", "--no-tags", "origin", f"pull/{pr_number}/head"],
        check=True,
    )


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
    base_sha = os.environ["BASE_SHA"]
    pr_number = os.environ["PR_NUMBER"]
    fetch_commits(pr_number)
    base = _run(["git", "merge-base", base_sha, "FETCH_HEAD"])
    sha = pick_baseline_sha(ancestors(base), has_visual_success)
    if sha is None:
        sys.exit(f"No successful Visual run on main within {MAX_ANCESTORS} commits of {base}")
    print(f"screenshot baseline {sha} (merge-base {base})", file=sys.stderr)
    write_sha(sha)


if __name__ == "__main__":
    main()
