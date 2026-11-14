# Local privacy and secret checks

CI detects committed content after upload. To run checks earlier, use a separate,
verified checkout of `repository-standards` pinned to the same commit as the
consumer workflow. The tooling environment must be outside the consumer's product
environment. These commands do not install a hook automatically.

## Prepare the tooling

Select an absolute checkout path and verify its commit against the consumer's
`uses:` pin before installation. Do not run setup from an unreviewed PR checkout.
Use Python 3.15.1 and uv 0.13.8. The installer verifies the selected
interpreter, source archive digests and dependency hashes.

```bash
PRIVACY_TOOL_ROOT=/absolute/path/to/verified/repository-standards
uv venv --python 3.15.1 "$PRIVACY_TOOL_ROOT/.venv"
bash "$PRIVACY_TOOL_ROOT/privacy/install.sh" \
  "$PRIVACY_TOOL_ROOT/.venv/bin/python" "$PRIVACY_TOOL_ROOT/.venv/privacy-guard"
```

Do not commit the environment or downloaded binary. Linux CI is the deployment
target. The installer also maps macOS and Windows architectures, but a platform
mapping alone is not evidence that its entire Python environment has passed
qualification. Unsupported binaries or missing wheels fail installation.

## Before a commit

Add this invocation to the clone's existing pre-commit mechanism, preserving its
other checks. Configure the absolute tooling and repository paths locally; do not
replace an existing hook or `core.hooksPath` without inspecting it.

```bash
"$PRIVACY_TOOL_ROOT/.venv/privacy-guard/venv/bin/python" -I \
  "$PRIVACY_TOOL_ROOT/scripts/privacy_guard.py" \
  --root /absolute/path/to/consumer \
  --binary "$PRIVACY_TOOL_ROOT/.venv/privacy-guard/bin/gitleaks" --staged
```

Use `--profile sensitive` to block the supported contact and identifier matches
throughout selected text. Staged mode reads the index rather than unstaged edits;
this catches content removed from the working copy but still staged for commit.
The personal-identifier scan covers complete blobs of changed staged/index files,
so unchanged files do not enter that incremental check.

## Before a push or release

Run a complete audit from a complete clone, or invoke it from the existing
pre-push mechanism:

```bash
"$PRIVACY_TOOL_ROOT/.venv/privacy-guard/venv/bin/python" -I \
  "$PRIVACY_TOOL_ROOT/scripts/privacy_guard.py" \
  --root /absolute/path/to/consumer \
  --binary "$PRIVACY_TOOL_ROOT/.venv/privacy-guard/bin/gitleaks" --mode full
```

Exit `1` identifies blocking findings and `2` identifies execution errors. Preserve
both as failures. A zero exit code still requires reading the scope, advisories
and coverage gaps. Full mode scans locally reachable secret history and current
tracked text; it is not a historical PII audit or a document-redaction service.

Verify installation using a disposable repository with synthetic canaries, not a
real credential or patient record. Do not test by uploading the canary. Install
hooks separately in each clone and confirm the Git client actually invokes them.
