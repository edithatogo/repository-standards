#!/usr/bin/env bash
set -euo pipefail
command -v gitleaks >/dev/null || { echo "Missing local gitleaks binary" >&2; exit 2; }
git diff --cached --binary --no-ext-diff | gitleaks stdin --redact --exit-code 1
