# frontend

React + Vite + TypeScript frontend.

## Setup

```bash
pnpm install
```

## Dev

```bash
pnpm dev           # localhost:3000, proxies /api to localhost:8000
pnpm test:watch    # vitest in watch mode
```

### skipping the login page

```bash
cp .env.local.example .env.local   # then restart vite
```

`.env.local` is gitignored. AuthBoot submits those credentials to the real
`/login/` endpoint on boot — it's not an auth bypass, so consent/onboarding
gates behave exactly as they do after a hand-typed login. Point it at a
different seed user to test another role. Logging out in-app still works
(auto-login only fires once per page load). `vite build` compiles the whole
path away, so it can't reach production.

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
