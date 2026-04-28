---
name: open-pr
description: Create a GitHub pull request for the current branch with a conventional-commit title. Handles branch creation/renaming if needed and pushes before opening. Use when the user asks to open a PR, create a PR, or "ship" a branch.
---

# open-pr

Open a GitHub pull request from the current branch to `main`.

## Branch naming

Branches must be named:

- **With a GitHub issue**: `<issue-number>-<short-kebab-description>` — e.g. `412-linkify-event-description`, `380-stub-canvas-getcontext`.
- **Without an issue**: `<short-kebab-description>` only — e.g. `tidy-axios-helpers`. Do **not** prefix with the user's name (no `leah/...`).

If the current branch doesn't fit this pattern and isn't already pushed, rename it before pushing:
```
git branch -m <new-name>
```
If it's already pushed under a non-conforming name, leave it alone and proceed.

Never work directly on `main`. If the user asks for a PR while on `main`, create a new branch off `origin/main` first (after `git fetch origin main`).

## Steps

1. **Inspect** in parallel:
   - `git status`
   - `git log main..HEAD --oneline` (all commits going into the PR — review **all** of them, not just HEAD)
   - `git diff main...HEAD` (full diverged diff)
   - `git rev-parse --abbrev-ref HEAD` and tracking info
2. **Verify branch name** matches the convention above; rename if needed and unpushed.
3. **Push** with `-u` if the branch isn't tracking a remote: `git push -u origin <branch>`.
4. **Draft the PR**:
   - **Title**: conventional commits format, same rules as the commit skill.
     - `<type>(<scope>): <short summary>`
     - Lowercase, imperative, no trailing period, under ~70 chars.
     - If linked to an issue, append ` (Issue <number>)` — e.g. `feat(events): autolink urls in event description (Issue 412)`.
   - **Body** (HEREDOC):
     ```
     ## Summary
     - <1-3 bullets on what changed and why>

     ## Test plan
     - [ ] <how to verify>
     ```
     If the PR closes an issue, add `Closes #<number>` on its own line under Summary.
5. **Create** the PR:
   ```
   gh pr create --title "..." --body "$(cat <<'EOF'
   ...
   EOF
   )"
   ```
6. **Return the PR URL.**

## Hard rules

- **Never merge** the PR (`.claude/rules/no-merge-prs.md`). Creating only.
- **Never push to `main`** directly.
- **Never force-push** without explicit user approval.
- **Never** add `Co-Authored-By` to commits or PR body (`.claude/rules/no-co-authored-by.md`).
- Use `(Issue 380)` style for issue refs in titles/bodies; PR refs themselves stay as `#<num>`.
- If `make agent-ci` hasn't been run for the latest changes, run it before pushing.

## Examples

Title:
```
feat(events): cohost invite approval flow (Issue 363)
fix(sms): use & separator on ios for sms: hrefs
refactor(perms): drop edit_welcome_message; gate template editor on approve_join_requests
```

Branch:
```
412-linkify-event-description
363-cohost-invite-approval
tidy-axios-helpers          # no issue
```
