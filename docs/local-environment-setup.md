# Local Environment Setup

Everything you need to install manually before `make` commands will work.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Python 3.13+** | Backend runtime | [python.org](https://www.python.org/downloads/) or `brew install python` |
| **uv** | Python package manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Flutter 3.x** | Frontend SDK | [flutter.dev/docs/get-started/install](https://flutter.dev/docs/get-started/install) |
| **Docker** | Runs PostgreSQL locally | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **1Password CLI** (`op`) | Pull dev credentials from 1Password | [docs/1password-cli.md](1password-cli.md) *(optional)* |

Verify everything is on your PATH:

```bash
python3 --version    # 3.13+
uv --version
flutter --version
docker --version
```

## First-time setup

### 1. Copy the env file

```bash
cp .env.example .env
```

The defaults work for local dev. `SECRET_KEY` can stay empty — Django falls back to a dev placeholder when `DEBUG=True`.

### 2. Install dependencies

```bash
make install    # uv sync + flutter pub get
```

### 3. Start the database

```bash
make db-start   # Starts PostgreSQL 16 in Docker on port 5432
```

Credentials: `postgresql://pda:pda@localhost:5432/pda` (matches the `.env` default).

### 4. Run migrations

```bash
make migrate
```

### 5. Create an admin user

```bash
make createsuperuser
```

### 6. Run the app

```bash
make dev    # Django on :8000 + Flutter on :3000 (concurrent)
```

Visit http://localhost:3000 for the app, http://localhost:8000/admin for Django admin.

## Optional: feedback button credentials

The GitHub App credentials for the feedback button are stored in 1Password. Without them the feedback button is simply disabled — you don't need them for general development.

To populate them, see [docs/1password-cli.md](1password-cli.md).

## Worktrees

If you're working in a git worktree (e.g. via `/spec`), the worktree won't have a `.env` file. The easiest fix is the `pda-env` alias (add to `~/.zshrc`):

```bash
alias pda-env='[[ $PWD == $HOME/repos/pda ]] && echo "already in pda root" || ln -sf ~/repos/pda/.env ./.env'
```

Run `pda-env` from the worktree directory to symlink the root `.env` in.

## Day-to-day commands

```bash
make dev              # Start both servers
make test             # Backend tests
make frontend-test    # Frontend tests
make ci               # Full pre-commit check — run before every commit
make migrate          # After changing models
make frontend-codegen # After changing Freezed/Riverpod models
make db-stop          # Stop PostgreSQL
```
