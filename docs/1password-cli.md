# 1Password CLI

The 1Password CLI (`op`) lets you pull secrets directly from 1Password into your local environment without copying values around. We use it to populate credentials for optional services (GitHub App, etc.) stored in the **Shared** vault.

## Install

**Homebrew (recommended):**

```bash
brew install 1password-cli
```

**Manual download:** https://app-updates.agilebits.com/product_history/CLI2

Full install guide (including other platforms): https://developer.1password.com/docs/cli/get-started

## Sign in via desktop app

The easiest way to authenticate is to link `op` to the 1Password desktop app — no separate sign-in needed.

1. Open **1Password** → **Settings** → **Developer**
2. Enable **"Integrate with 1Password CLI"**
3. Done — `op` will use your desktop app session automatically

Full guide: https://developer.1password.com/docs/cli/app-integration

Verify it's working:

```bash
op whoami
```

## Populate GitHub App credentials

The GitHub App credentials for the feedback button are stored in the **PDAFeedbackForm** item (Shared vault). To add them to your `.env`:

```bash
echo "GITHUB_APP_ID=$(op item get PDAFeedbackForm --fields 'App ID')" >> .env
echo "GITHUB_APP_INSTALLATION_ID=$(op item get PDAFeedbackForm --fields 'PDA Installation ID')" >> .env
echo "GITHUB_APP_PRIVATE_KEY=$(op read 'op://Shared/PDAFeedbackForm/add more/pdafeedbackform.2026-03-31.private-key.pem' | base64 | tr -d '\n')" >> .env
echo "GITHUB_REPO=ProteinDeficientsAnonymous/pda" >> .env
```

Or set them as shell exports for a single session:

```bash
export GITHUB_APP_ID=$(op item get PDAFeedbackForm --fields "App ID")
export GITHUB_APP_INSTALLATION_ID=$(op item get PDAFeedbackForm --fields "PDA Installation ID")
export GITHUB_APP_PRIVATE_KEY=$(op read "op://Shared/PDAFeedbackForm/add more/pdafeedbackform.2026-03-31.private-key.pem" | base64 | tr -d '\n')
export GITHUB_REPO=ProteinDeficientsAnonymous/pda
```
