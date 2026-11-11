#!/usr/bin/env bash
# Exit 0 for detected AI code, 1 for absent, 2+ for inspection failures.
set -euo pipefail
git rev-parse --is-inside-work-tree >/dev/null || exit 2
if git ls-files -z | grep -z -Ei '(^|/)(.*agent.*|.*rag.*|.*mcp.*|promptfooconfig\.yaml|ai-security.*)\.(py|rs|ts|tsx|js|json|ya?ml)$' >/dev/null; then
  exit 0
fi
if git grep --cached -I -i -q -E '(langchain|llama_index|llamaindex|gliner|promptfoo|presidio|modelcontextprotocol|@modelcontextprotocol|from[[:space:]]+openai|import[[:space:]]+openai|anthropic|ollama)' -- '*.py' '*.rs' '*.ts' '*.tsx' '*.js' 'Cargo.toml' 'pyproject.toml' 'package.json' 'requirements*.txt'; then
  exit 0
fi
exit 1
