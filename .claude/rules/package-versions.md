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

## Flutter / Dart

```bash
flutter pub add <package>  # resolves latest compatible version
```

If manually specifying a version in `pubspec.yaml`, check first:
```bash
flutter pub outdated
# or look up on pub.dev
```

## Rules

- Never hardcode a version you found in documentation or examples — it may be outdated.
- Use `^` (caret) constraints in both `pyproject.toml` and `pubspec.yaml` to allow compatible updates.
- After adding a package, note it in `DEPENDENCIES.md` if it's a significant dependency.
