# Automated Versioning + Changelog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On every push to `main`, automatically compute the next semver version from conventional commits, update `CHANGELOG.md`, bump both package files to match, tag the release, and publish a GitHub Release.

**Architecture:** A root `package.json` hosts semantic-release + plugins. `.releaserc.json` wires commit-analyzer → release-notes-generator → changelog → a Python `prepareCmd` that bumps both package files → git (commits assets back to `main` with `[skip ci]`) → github (tag + Release). A GitHub Actions workflow (`release.yml`) runs it on push to `main`, authenticated with a branch-protection-bypass token.

**Tech Stack:** semantic-release 24 (Node), `@semantic-release/changelog`, `@semantic-release/exec`, `@semantic-release/git`, `@semantic-release/github`; a small Python 3.13 script for the version bump; GitHub Actions.

## Global Constraints

- **Single app version** — one version stream for the whole repo; backend + frontend share it.
- **Conventional commits ruleset (default):** `feat` → minor, `fix`/`perf` → patch, `BREAKING CHANGE` → major; `chore`/`docs`/`test`/`ci`/`refactor` → no release.
- **Assets committed back to `main`:** `CHANGELOG.md`, `frontend/package.json`, `pyproject.toml`.
- **Release commit message:** `chore(release): ${nextRelease.version} [skip ci]` — the `[skip ci]` marker is mandatory (loop prevention).
- **Root package manager is npm** (isolated from the frontend's pnpm workspace). The root lockfile is `package-lock.json`.
- **Backend version field:** `[project].version` in `pyproject.toml`, currently `"0.1.0"`.
- **Frontend version field:** top-level `"version"` in `frontend/package.json`, currently `"0.0.0"`.
- **Node 22, Python 3.13** in CI (matches existing workflows).
- **Never edit files on `main` directly** — all work is on branch `feat-581-versioning-changelog` in this worktree.
- Commit message subjects follow the repo's conventional-commit style; reference the issue as `(Issue 581)` in bodies where relevant, not `#581`.

---

### Task 1: Version-bump script + its test

A single Python script rewrites the version field in both package files. It is a plain utility (no Django, no DB), so its test runs without the `db` fixture. Building it first means the release config in Task 2 can reference a script that already works and is tested.

**Files:**
- Create: `scripts/set_release_version.py`
- Test: `backend/tests/test_set_release_version.py`

**Interfaces:**
- Consumes: nothing (leaf utility).
- Produces: CLI `python scripts/set_release_version.py <version>` — rewrites `[project].version` in `pyproject.toml` and top-level `"version"` in `frontend/package.json` to `<version>`. Importable functions `set_pyproject_version(path: Path, version: str) -> None` and `set_package_json_version(path: Path, version: str) -> None`, each rewriting only the version field and leaving all other bytes unchanged.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_set_release_version.py`:

```python
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
        '[project]\n'
        'name = "pda"\n'
        'version = "0.1.0"\n'
        'description = "keep me"\n'
        '\n'
        '[tool.ruff]\n'
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
    p.write_text(json.dumps({"name": "frontend", "version": "0.0.0", "type": "module"}, indent=2) + "\n")
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest backend/tests/test_set_release_version.py -p no:cacheprovider -v`
Expected: FAIL — `scripts/set_release_version.py` does not exist (import error / FileNotFoundError).

- [ ] **Step 3: Write minimal implementation**

`scripts/set_release_version.py`:

```python
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
```

Note: `set_pyproject_version` matches the FIRST `version = "..."` line via `count=1`. In `pyproject.toml` the `[project].version` line is the first such assignment (dependency version constraints live inside a list, not as `version = "..."` lines), so this is safe. The test's `[tool.ruff]` decoy proves only one line is rewritten.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest backend/tests/test_set_release_version.py -p no:cacheprovider -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Verify against the real files (dry check, no write)**

Run:
```bash
uv run python -c "import importlib.util,pathlib; s=pathlib.Path('scripts/set_release_version.py'); spec=importlib.util.spec_from_file_location('srv',s); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('pyproject re matches:', bool(__import__('re').search(r'(?m)^version\s*=\s*\"', pathlib.Path('pyproject.toml').read_text())))"
```
Expected: `pyproject re matches: True`

- [ ] **Step 6: Commit**

```bash
git add scripts/set_release_version.py backend/tests/test_set_release_version.py
git commit -m "feat(release): version-bump script for pyproject + package.json (Issue 581)"
```

---

### Task 2: Root package.json + semantic-release config

Add the root `package.json` (semantic-release + plugins) and `.releaserc.json`. Validate the config with a real `--dry-run` against the git history so we know it parses and computes a version before any workflow exists.

**Files:**
- Create: `package.json` (repo root)
- Create: `.releaserc.json` (repo root)
- Create/Modify: `.gitignore` (add root `node_modules/`)

**Interfaces:**
- Consumes: `scripts/set_release_version.py` from Task 1 (via `prepareCmd`).
- Produces: a working `npx semantic-release --dry-run` at repo root; the assets list and release-commit message defined in Global Constraints.

- [ ] **Step 1: Create the root package.json**

`package.json` (repo root):

```json
{
  "name": "pda",
  "private": true,
  "version": "0.1.0",
  "description": "release tooling for the pda monorepo",
  "devDependencies": {
    "@semantic-release/changelog": "^6.0.3",
    "@semantic-release/exec": "^6.0.3",
    "@semantic-release/git": "^10.0.1",
    "semantic-release": "^24.2.0"
  }
}
```

- [ ] **Step 2: Create the release config**

`.releaserc.json` (repo root):

```json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    [
      "@semantic-release/changelog",
      { "changelogFile": "CHANGELOG.md" }
    ],
    [
      "@semantic-release/exec",
      { "prepareCmd": "python scripts/set_release_version.py ${nextRelease.version}" }
    ],
    [
      "@semantic-release/git",
      {
        "assets": ["CHANGELOG.md", "frontend/package.json", "pyproject.toml"],
        "message": "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
      }
    ],
    "@semantic-release/github"
  ]
}
```

- [ ] **Step 3: Ignore root node_modules**

Ensure `.gitignore` (repo root) contains a line for the root `node_modules/`. Check first:

Run: `grep -qxF 'node_modules/' .gitignore && echo present || echo missing`

If `missing`, append it:

Run: `printf '\n# root release tooling\nnode_modules/\npackage-lock.json\n' >> .gitignore`

(We commit `package.json` but not the root lockfile — CI generates it fresh; keeping it out avoids confusing it with the frontend's pnpm lock. If you prefer a committed lockfile for reproducibility, remove `package-lock.json` from `.gitignore` and commit it in Step 6 — but the workflow in Task 3 must then use `npm ci` with that lockfile present. Default: gitignore it and use `npm install` in the workflow.)

- [ ] **Step 4: Install and dry-run**

Run:
```bash
npm install --no-audit --no-fund
GITHUB_TOKEN=dummy npx semantic-release --dry-run --no-ci 2>&1 | tail -30
```
Expected: semantic-release loads all plugins without a config error, reports the analyzed commits and the next version it *would* release (or "no new version is released" if the branch has only non-releasing commits). It must NOT error on plugin resolution or config parsing. The `--no-ci` flag lets it run off a CI environment; `GITHUB_TOKEN=dummy` satisfies the github plugin's presence check in dry mode.

If it reports a git-auth or push error, that's expected in `--dry-run` only if it reaches the publish phase — dry-run should stop before pushing. If it complains the branch is not `main`, add `--branches "$(git rev-parse --abbrev-ref HEAD)"` is NOT valid; instead confirm dry-run recognizes the current branch via `GITHUB_REF`. Simplest: the assertion is only that plugins load and a version is computed; ignore push-phase messages.

- [ ] **Step 5: Confirm the prepareCmd script bumps both files (against temp copies — never mutate tracked files)**

Do NOT run the bump against the real tracked files. Copy them to a temp dir,
bump the copies, and diff the copies, so nothing tracked is ever modified (this
project forbids `git checkout`/`git restore` on the working tree):

```bash
T=$(mktemp -d)
mkdir -p "$T/frontend"
cp pyproject.toml "$T/pyproject.toml"
cp frontend/package.json "$T/frontend/package.json"
uv run python -c "
import importlib.util, pathlib
s = pathlib.Path('scripts/set_release_version.py')
spec = importlib.util.spec_from_file_location('srv', s)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.set_pyproject_version(pathlib.Path('$T/pyproject.toml'), '9.9.9')
m.set_package_json_version(pathlib.Path('$T/frontend/package.json'), '9.9.9')
"
grep -n '9.9.9' "$T/pyproject.toml" "$T/frontend/package.json"
echo '--- tracked files untouched: ---'
git diff --stat
rm -rf "$T"
```

Expected: both temp files show `9.9.9` in their version fields, and `git diff --stat` reports NO changes to tracked files (the real `pyproject.toml` / `frontend/package.json` were never written). This proves the two bump functions work against real-shaped files without touching the working tree.

- [ ] **Step 6: Commit**

```bash
git add package.json .releaserc.json .gitignore
git commit -m "feat(release): semantic-release config + root package (Issue 581)"
```

---

### Task 3: Release workflow

Add the GitHub Actions workflow that runs semantic-release on push to `main`. It can't be end-to-end tested until it's on `main` with the bypass token in place, so this task's deliverable is a valid, self-consistent workflow file plus a documented manual-setup checklist.

**Files:**
- Create: `.github/workflows/release.yml`
- Modify: `README.md` (short "Releases" section pointing at the manual setup)

**Interfaces:**
- Consumes: root `package.json`, `.releaserc.json` (Task 2); `scripts/set_release_version.py` (Task 1).
- Produces: the `Release` workflow; requires repo secret `RELEASE_TOKEN`.

- [ ] **Step 1: Create the workflow**

`.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    branches: [main]

concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  release:
    name: Release
    runs-on: ubuntu-latest
    if: ${{ !contains(github.event.head_commit.message, '[skip ci]') }}
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
          persist-credentials: false
          token: ${{ secrets.RELEASE_TOKEN }}

      - uses: actions/setup-node@v6
        with:
          node-version: "22"

      - uses: actions/setup-python@v6
        with:
          python-version: "3.13"

      - name: Install release tooling
        run: npm install --no-audit --no-fund

      - name: Run semantic-release
        run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.RELEASE_TOKEN }}
```

- [ ] **Step 2: Lint the workflow YAML**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 3: Sanity-check the loop guard and token wiring**

Confirm by inspection (and via grep) that:
- the `if:` guard skips commits containing `[skip ci]`,
- both `checkout.token` and the `GITHUB_TOKEN` env use `secrets.RELEASE_TOKEN`,
- `fetch-depth: 0` and `persist-credentials: false` are present.

Run: `grep -nE 'skip ci|RELEASE_TOKEN|fetch-depth: 0|persist-credentials: false' .github/workflows/release.yml`
Expected: matches for all four.

- [ ] **Step 4: Add a Releases section to the README**

Append to `README.md` (keep it lowercase to match repo copy conventions where the README already does so — match the surrounding style of the file):

```markdown
## releases

versioning and the changelog are automated with semantic-release. every push
to `main` runs `.github/workflows/release.yml`, which computes the next semver
version from conventional commits, updates `CHANGELOG.md`, bumps the version in
`frontend/package.json` and `pyproject.toml`, tags the release, and
publishes a github release.

**one-time setup (owner):**
1. create a `RELEASE_TOKEN` repo actions secret — a fine-grained PAT or github
   app token with `contents: write` on this repo, on an identity allowed to
   bypass `main` branch protection.
2. add that identity to the branch-protection bypass allowlist (main requires a
   PR + approval; `enforce_admins` is off).
3. push a seed tag on `main` before the first release:
   `git tag v0.1.0 && git push origin v0.1.0`
   (prevents the first changelog from spanning the entire history).

commits follow conventional commits: `feat` → minor, `fix`/`perf` → patch,
`BREAKING CHANGE` → major; `chore`/`docs`/`test`/`refactor` → no release.
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/release.yml README.md
git commit -m "feat(release): add release workflow + docs (Issue 581)"
```

---

### Task 4: Final verification + PR

Run the repo's pre-PR gate and open the draft PR.

**Files:** none (verification + PR).

- [ ] **Step 1: Run the version-bump test once more in isolation**

Run: `uv run pytest backend/tests/test_set_release_version.py -p no:cacheprovider -q`
Expected: `3 passed`.

- [ ] **Step 2: Confirm no stray version bumps are staged**

Run: `git status --short && git diff --stat origin/main -- frontend/package.json pyproject.toml`
Expected: `frontend/package.json` and `pyproject.toml` are UNCHANGED vs `origin/main` (the automation bumps them at release time, not now). If either shows a diff, STOP — do not run `git checkout`/`git restore` (forbidden on the working tree here). Report the unexpected diff; it means an earlier probe wrote a tracked file, which the Task 2 Step 5 temp-copy approach is designed to prevent.

- [ ] **Step 3: Run the frontend + backend CI gate**

Run: `make agent-ci`
Expected: passes. (This touches no runtime code, so failures would indicate a lint/format issue in the new files — fix and re-run.)

- [ ] **Step 4: Push and open the draft PR**

Use the `/open-pr` skill (targets `main`, draft mode, conventional-commit title). Suggested title: `feat(release): automated versioning + changelog via semantic-release`. Body links Issue 581 and includes the owner one-time-setup checklist from the README so the reviewer knows the token + seed-tag steps are manual.

---

## Post-merge manual steps (owner, tracked on the PR)

These cannot be automated by this PR and must happen before the first real release works end-to-end:

1. Create `RELEASE_TOKEN` secret (fine-grained PAT / GitHub App, `contents: write`, bypass-capable identity).
2. Add that identity to `main`'s branch-protection bypass allowlist.
3. After merge, push seed tag: `git tag v0.1.0 && git push origin v0.1.0`.

Until step 1–2 are done, the `Release` workflow will run and fail at the push-back step (no permission to write to protected `main`) — a clean, expected failure that surfaces the missing token rather than corrupting anything.

---

## Self-Review

**Spec coverage:**
- Single app version → Global Constraints + Task 1 bumps both files to the same value. ✓
- Trigger on every push to main → Task 3 workflow `on: push: branches: [main]`. ✓
- Sync all three artifacts → `.releaserc.json` git `assets` (Task 2) + bump script (Task 1). ✓
- Committed CHANGELOG.md via bypass token → `@semantic-release/changelog` + git plugin (Task 2), `RELEASE_TOKEN` (Task 3). ✓
- Root package.json (new) → Task 2. ✓
- pyproject + package.json version write → Task 1 script. ✓
- Loop prevention (`[skip ci]` + `if:` guard) → Global Constraints + Task 3 Step 3. ✓
- Seed tag → documented in README (Task 3) + post-merge steps. ✓
- Branch-protection bypass token, owner-owned manual step → README + post-merge section. ✓
- Out of scope (app UI version, per-package streams, prerelease channels) → not planned. ✓
- Testing: dry-run (Task 2 Step 4), loop-guard inspection (Task 3 Step 3), bump-script unit tests (Task 1). ✓

**Placeholder scan:** no TBD/TODO; every code step shows full code. ✓

**Type consistency:** `set_release_version.py` exposes `set_pyproject_version`, `set_package_json_version`, `main` — used consistently in Task 1 test and Task 2 `prepareCmd`. Asset list and commit message identical across Global Constraints and Task 2. ✓
