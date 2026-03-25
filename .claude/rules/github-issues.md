---
paths:
  - ".github/**"
---

# GitHub Issue Formatting

Standards for creating and updating issues in this project.

## Title

Prefix with scope tag in brackets, then a concise description:

```
[scope] Short imperative description
```

| Scope | When |
|-------|------|
| `[fe]` | Frontend-only |
| `[be]` | Backend-only |
| `[fe/be]` or `[be/fe]` | Both (lead with the heavier side) |
| `[bot]` | WhatsApp bot microservice |
| `[infra]` | Infrastructure, deployment, config |

## Labels

Apply **all** that fit. Every issue needs at least one area label and one type label.

**Area:** `backend`, `frontend`, `infra`
**Type:** `feature`, `bug`, `testing`, `design`, `deployment`

## Body Structure

```markdown
## Description
One paragraph explaining what and why.

## Tasks
- Concrete, implementable bullet points
- Reference specific files/endpoints/models when known
- For cross-cutting work, split into subsections:

## Backend tasks
- ...

## Frontend tasks
- ...

## Dependencies
- Depends on #N (brief reason)

## Notes
- Design decisions, open questions, edge cases
```

### Section rules

- **Description** — always present. What the change is and why it matters.
- **Tasks** — always present. Actionable items, not vague goals. Reference file paths, model names, endpoint paths, and permission keys by name.
- **Dependencies** — only when the issue blocks on or is blocked by another. Use `#N` references. Can also appear as a one-liner at the top of the body (`Depends on #19.`) for simple cases.
- **Notes** — optional. Constraints, edge cases, or decisions that aren't tasks.

## Conventions

- Reference API endpoints with method + path: `POST /api/community/join-request/`
- Reference models by name: `Event`, `JoinRequest`, `User`
- Reference permissions by key: `manage_events`, `approve_join_requests`
- Use fenced code blocks for message formats, file trees, and code snippets
- Keep tasks specific enough that someone can implement without re-reading the whole codebase
- One issue per logical unit of work — split fe/be if they can be done independently, combine if tightly coupled
