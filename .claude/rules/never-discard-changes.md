# Never Discard Uncommitted Changes

**NEVER** use any of the following to discard working tree changes:

- `git restore <file>`
- `git checkout -- <file>`
- `git clean -f`
- `git reset --hard`
- `git stash drop` (without confirming with the user first)

If you encounter uncommitted changes that are not yours or are unrelated to your task:

1. **Re-stash them**: `git stash push <specific files>` with a descriptive message
2. **Or leave them alone** — do not touch files that aren't part of your task
3. **Ask the user** if you're unsure what to do with them

Uncommitted changes may be the user's in-progress work. Destroying them is irreversible.
