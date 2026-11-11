#!/usr/bin/env bash
# Exit 0 if tracked agent/AI code found; exit 1 if absent; 2 for inspection failure.
set -euo pipefail
git rev-parse --is-inside-work-tree >/dev/null || exit 2
if git ls-files -z | grep -z -Eiq '(^|/)(.*agent.*|.*rag.*|.*mcp.*|promptfooconfig\.yaml|ai-security.*)\.(py|rs|ts|tsx|js|json|ya?ml)$'; then
  exit 0
fi
if git grep --cached -I -i -q -E '(langchain|llama_index|llamaindex|gliner|promptfoo|presidio|modelcontextprotocol|@modelcontextprotocol|from[[:space:]]+openai|import[[:space:]]+openai|anthropic|ollama)' -- '*.py' '*.rs' '*.ts' '*.tsx' '*.js' 'Cargo.toml' 'pyproject.toml' 'package.json' 'requirements*.txt'; then
  exit 0
fi
exit 1
