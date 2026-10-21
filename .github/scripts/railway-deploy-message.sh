#!/usr/bin/env bash
set -euo pipefail

ref="${1:-HEAD}"
subject="$(git log -1 --pretty=format:%s "${ref}")"
subject="${subject% \[skip ci\]}"
sha="$(git rev-parse --short=7 "${ref}")"
# semantic-release stores changelog bullets in the commit body
bullets="$(
  git log -1 --pretty=format:%b "${ref}" \
    | { grep -E '^[*•-] ' || true; } \
    | sed -E 's/^[*•-][[:space:]]*//; s/\[([^]]+)\]\([^)]+\)/\1/g; s/\*\*//g; s/ \([a-f0-9]{7,40}\)$//' \
    | awk 'NR <= 5 { printf "%s%s", (NR > 1 ? "; " : ""), $0 }'
)"
if [ -n "${bullets}" ]; then
  deploy_message="${sha} ${subject}: ${bullets}"
else
  deploy_message="${sha} ${subject}"
fi
printf '%s' "${deploy_message}" | tr -d '\r\n' | cut -c1-250
printf '\n'
