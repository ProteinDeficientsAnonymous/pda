---
paths:
  - "**/package.json"
  - "**/pyproject.toml"
  - "**/pubspec.yaml"
  - "**/requirements*.txt"
---

# Package Version Policy

When adding or recommending any new package dependency, always look up and use the **latest stable version**.

## Python / uv

```bash
uv add <package>  # uv resolves latest by default
```

If manually specifying a version in `pyproject.toml`, check first:
```bash
uv pip index versions <package>
```

## Frontend (pnpm)

```bash
pnpm add <package>  # resolves latest compatible version
```

## Rules

- Never hardcode a version you found in documentation or examples — it may be outdated.
- Use `^` (caret) constraints in `pyproject.toml` and `package.json` to allow compatible updates.
- After adding a package, note it in `DEPENDENCIES.md` if it's a significant dependency.
