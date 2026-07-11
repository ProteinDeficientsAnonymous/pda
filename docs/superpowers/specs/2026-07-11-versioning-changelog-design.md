# Automated versioning + changelog (semantic-release)

**Issue:** #581
**Date:** 2026-07-11
**Status:** approved design, ready for planning

## Goal

Every push to `main` automatically computes the next semver version from
conventional commits, updates a root `CHANGELOG.md`, bumps the two package
files to match, tags the release, and publishes a GitHub Release. No manual
version bookkeeping.

## Decisions (from brainstorming)

- **Single app version.** One version for the whole app. Backend and frontend
  are released together (single Railway deploy), so they share one version
  stream — not independent per-package versioning.
- **Trigger: every push to `main`.** A GitHub Actions job runs semantic-release
  on each merge. No-op when the commits since the last release are only
  chore/docs/test (nothing that warrants a release).
- **Sync all three artifacts.** semantic-release writes the computed version to
  `CHANGELOG.md`, `frontend/package.json`, and `pyproject.toml`, and
  commits them back to `main`. The package files stay honest.
- **Real committed `CHANGELOG.md`** in the repo tree (not Releases-only),
  authenticated with a token that bypasses branch protection.

## The load-bearing constraint: branch protection

`main` is protected: PRs require 1 approval + passing `Backend`/`Frontend`
checks, and `enforce_admins` is **false**. semantic-release's `@semantic-release/git`
plugin pushes a version-bump commit directly to `main`, which protection blocks
for a normal `GITHUB_TOKEN`.

**Resolution:** the release workflow checks out and pushes using a **privileged
token that bypasses branch protection** — either:
- a fine-grained **Personal Access Token** on an account exempt from protection, or
- a **GitHub App** installation token added to the protection bypass list.

The release commit message carries `[skip ci]` so the push does not re-trigger CI
or the release workflow (loop prevention).

> **Manual step, owner-owned:** creating the token and (if using a PAT) confirming
> the account can bypass protection is done by the repo owner, not by the
> implementation. The plan documents exact steps but does not create tokens or
> alter protection settings automatically.

## Components

### 1. Root `package.json` (new)

The repo has no root `package.json` today. semantic-release runs from the repo
root, so add a minimal **private** root `package.json` holding the
semantic-release devDependency and the release scripts. Keeps
`frontend/package.json` free of release tooling.

```jsonc
{
  "name": "pda",
  "private": true,
  "version": "0.1.0",
  "devDependencies": {
    "semantic-release": "^24",
    "@semantic-release/changelog": "^6",
    "@semantic-release/git": "^10",
    "@semantic-release/exec": "^6"
  }
}
```

(`commit-analyzer`, `release-notes-generator`, `github` ship inside
`semantic-release` core.)

### 2. `.releaserc.json` (release config)

```jsonc
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    ["@semantic-release/changelog", { "changelogFile": "CHANGELOG.md" }],
    ["@semantic-release/exec", {
      "prepareCmd": "python scripts/set_release_version.py ${nextRelease.version}"
    }],
    ["@semantic-release/git", {
      "assets": ["CHANGELOG.md", "frontend/package.json", "pyproject.toml"],
      "message": "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
    }],
    "@semantic-release/github"
  ]
}
```

The default conventional-commits ruleset applies: `feat` → minor, `fix`/`perf`
→ patch, `BREAKING CHANGE` → major; `chore`/`docs`/`test`/`ci`/`refactor` →
no release.

### 3. Version-write into the package files

A single `prepareCmd` script — `scripts/set_release_version.py` — owns **both**
package-file bumps, so there is one place to reason about and test:

- **`pyproject.toml`** — rewrite the `[project].version` line to the new
  version.
- **`frontend/package.json`** — rewrite its `version` field to the new version.

One script (rather than the native `@semantic-release/npm` plugin) avoids
npm-workspace surprises between the root release package and the frontend's pnpm
workspace, and keeps the frontend bump identical in mechanism to the backend
bump. Running it through `@semantic-release/exec`'s `prepareCmd` keeps the writes
inside semantic-release so `--dry-run` skips them correctly.

### 4. `.github/workflows/release.yml`

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
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, '[skip ci]')"
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
          persist-credentials: false
          token: ${{ secrets.RELEASE_TOKEN }}
      - uses: actions/setup-node@v6
        with: { node-version: "22" }
      - uses: actions/setup-python@v6
        with: { python-version: "3.13" }
      - run: npm ci
      - run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.RELEASE_TOKEN }}
```

- `fetch-depth: 0` — semantic-release needs full history + tags.
- Python is set up because the `prepareCmd` script that bumps `pyproject.toml`
  runs under Python.
- The `if:` guard plus `[skip ci]` in the release commit prevents the workflow
  from re-triggering on its own bump commit.
- `RELEASE_TOKEN` is the bypass token (repo secret).

### 5. Seed tag (first-run baseline)

Before the first real release, create a baseline tag (e.g. `v0.1.0`) on the
current `main` HEAD. Without it, semantic-release treats the entire history as
one release and generates an enormous first changelog. The seed tag makes the
first automated release contain only commits *after* it.

## Data flow

```
merge PR to main
  → CI (Backend, Frontend) passes
  → release.yml runs (skipped if head commit has [skip ci])
  → semantic-release reads commits since last tag
  → computes next version
  → writes CHANGELOG.md, bumps frontend/package.json + pyproject.toml
  → commits assets to main via RELEASE_TOKEN, message "chore(release): X.Y.Z [skip ci]"
  → tags vX.Y.Z
  → creates GitHub Release with generated notes
```

## Edge cases / risks

- **Infinite loop.** Mitigated two ways: `[skip ci]` in the release commit *and*
  the `if:` guard on the workflow. Both are required — belt and suspenders.
- **First run without seed tag.** Produces a giant changelog. Mitigated by the
  seed tag step.
- **Token exposure.** `RELEASE_TOKEN` can push to protected `main`. Scope it to
  the minimum (contents:write on this repo), document rotation, prefer a
  fine-grained PAT or GitHub App over a classic PAT.
- **Non-releasing pushes.** chore/docs/test-only merges → semantic-release exits
  0 with "no release published." Expected, not an error.
- **CI ordering.** Release runs on `push` to main independently of the PR CI.
  It does not gate on CI green (the PR already required green checks to merge).
  Acceptable; noted so no one expects release to re-run tests.
- **Root package manager.** Frontend uses pnpm; the root release package uses
  npm to stay isolated from the frontend workspace. Keep the root lockfile
  (`package-lock.json`) out of the frontend's pnpm workspace.

## Explicitly out of scope

- Surfacing the version in the app UI or a `/api/version` endpoint (deferred;
  can be added later once the version files are authoritative).
- Independent per-package version streams.
- Pre-release / beta channels (`next`, `beta` branches).
- Changing branch protection rules (owner decides separately).

## Testing / validation

- **Dry run:** run `npx semantic-release --dry-run` on a branch to prove the
  version computation and generated notes without publishing.
- **Loop check:** verify the `[skip ci]` release commit does not re-trigger
  `release.yml` (inspect Actions after the first live release).
- **Seed-tag check:** confirm the first real changelog only spans commits after
  the seed tag.
- **version bump script:** unit-test `set_release_version.py` against fixture
  copies of `pyproject.toml` and `package.json` to confirm it rewrites only the
  version fields and leaves the rest byte-for-byte unchanged.

## Manual steps for the owner (documented, not automated)

1. Create `RELEASE_TOKEN` (fine-grained PAT or GitHub App token) with
   contents:write on this repo, on an identity that can bypass `main`
   protection. Add it as a repo Actions secret.
2. If using a PAT: add that account to the branch-protection bypass allowlist
   (or ensure it's an admin and flip the relevant setting), since
   `enforce_admins` is currently false.
3. Push the seed tag `v0.1.0` to `main` HEAD before the first merge that should
   trigger a release.
