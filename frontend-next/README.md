# frontend-next

React + Vite + TypeScript replacement for the Flutter web frontend. See `/FLUTTER_TO_VITE_REACT_MIGRATION.md` at the repo root for the full migration plan.

## Setup

```bash
pnpm install
```

## Dev

```bash
pnpm dev           # localhost:3000, proxies /api to localhost:8000
pnpm test:watch    # vitest in watch mode
```

## CI

```bash
pnpm typecheck     # tsc -b
pnpm lint          # eslint with zero warnings
pnpm test          # vitest run
pnpm build         # tsc -b && vite build
```

## API types

Generated from the Django Ninja OpenAPI schema. Run the backend first:

```bash
# in repo root
make run            # Django on localhost:8000
# then
pnpm types:api      # writes src/api/types.gen.ts
```

The generated file is committed so builds pass without a backend running; regenerate whenever the API surface changes.
