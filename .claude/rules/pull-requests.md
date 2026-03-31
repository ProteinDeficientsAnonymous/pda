---
paths:
  - ".github/**"
---

# Pull Request Conventions

## Base Branch

**All PRs default to `staging` as the base branch**, not `main`.

```bash
gh pr create --draft --base staging
```

Only target `main` directly for hotfixes that must go to production immediately — and only with explicit confirmation.

## Other Conventions

- Always open in draft mode
- Titles use conventional commit format: `type(scope): description`
- Check for PR templates at `.github/PULL_REQUEST_TEMPLATE.md` before writing the description
