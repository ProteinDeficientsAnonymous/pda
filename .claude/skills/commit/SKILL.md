---
name: commit
description: Stage and commit changes using conventional commits. Run cheap local checks first (full CI is a pre-PR gate, not per-commit — GitHub re-runs it on every push), then create a properly formatted commit. Use when the user asks to commit, save, or check in changes.
---

# commit

Stage and create a commit using **conventional commits** format.

## Steps

1. **Run cheap checks first**: typecheck + the tests you touched (e.g. `make agent-typecheck`, `make agent-frontend-typecheck`, `make agent-test-since`). If they fail, surface the errors and stop — do not commit. The full `make agent-ci` suite is a **pre-PR gate**, not a per-commit one: GitHub re-runs CI on every push, so run the umbrella once before the PR is review-ready (see `.claude/skills/open-pr`), not on every commit.
2. **Inspect state** in parallel:
   - `git status` (no `-uall`)
   - `git diff` (staged + unstaged)
   - `git log -5 --oneline` to match local style
3. **Draft the message** in conventional commits format:
   ```
   <type>(<scope>): <short summary>
   ```
   - **Types**: `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `ci`, `perf`, `style`
   - **Scope**: the affected area (e.g. `events`, `sms`, `vetting`, `fe`, `admin`, `perms`). Omit if cross-cutting.
   - **Summary**: lowercase, imperative ("add", "fix", "drop"), no trailing period.
   - **Issue ref**: if the work relates to a GitHub issue, append ` (Issue <number>)` to the summary. Use `(Issue 380)` style — never `#380` for issue refs in commits.
   - Keep the subject under ~72 chars. Add a body only if the *why* isn't obvious.
4. **Stage explicitly** — name files; never `git add -A` or `git add .`. Skip anything that looks like secrets (`.env`, credentials).
5. **Commit** via HEREDOC so formatting is preserved.
6. **Verify** with `git status` after.

## Hard rules

- **Never** add a `Co-Authored-By` trailer (see `.claude/rules/no-co-authored-by.md`).
- **Never** use `--no-verify`, `--amend` (unless the user explicitly asks), or skip hooks.
- **Never** push as part of this skill — committing only.
- If pre-commit hooks fail, fix the underlying issue and create a **new** commit (do not amend).
- Only commit when the user has explicitly asked to commit.

## Examples

```
feat(events): autolink urls in event description (Issue 412)
fix(rsvp): match my guest record by user id, not status (Issue 368)
chore: drop unused SITE_URL setting and event_url helper
refactor(fe): centralize axios error inspection in apiErrors helpers (Issue 388)
ci: enforce types.gen.ts + openapi schema parity in check-codes (Issue 379)
```
