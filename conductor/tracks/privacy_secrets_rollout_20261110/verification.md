# Shared implementation verification

Local verification on 2026-11-10 used Python 3.12.14, Presidio Analyzer and
Anonymizer 2.2.366, Gitleaks 8.30.1 and Zizmor 1.32.0. The Gitleaks Linux x64
archive matched the upstream SHA-256 recorded in `scripts/install_gitleaks.py`.
The complete Python dependency set resolved and installed using the hash lock.

| Command or check | Observed result |
| --- | --- |
| `PYTHONPATH=scripts GITLEAKS_BINARY=/path/to/verified/gitleaks python -m unittest discover -s tests -v` | 84 tests passed; real Presidio and Gitleaks integration cases executed |
| `ruff check` and `ruff format --check` on the seven added Python source/test files | Passed |
| `zizmor --no-progress --format json .github/actions/privacy-secrets/action.yml .github/workflows/privacy-guard-tests.yml` | Passed with zero findings; offline mode, remote audits not claimed |
| `python -I scripts/privacy_guard.py --root . --staged --binary /path/to/verified/gitleaks` | Both tools exited successfully; zero findings, 21 selected text files scanned with zero skips at that checkpoint |
| `git diff --cached --check` | Passed |

The staged scan checkpoint preceded this verification record and the final
documentation-only status updates. Its result does not substitute for the
exact-commit hosted canary.

Behavioral evidence includes checksum mismatch rejection, added-then-deleted
secrets, initial and subsequent staged changes, committed blobs instead of a
modified worktree, shallow-history rejection, symlink/submodule/LFS/oversize
coverage accounting, bounded reports, newline filenames, missing tools, malformed
reports, unavailable commits, checksum validation of personal identifiers,
public citation contacts, sensitive data paths and socket-denied email detection.

Two discovered failures were fixed before publication: Python setup needed `-I`
to prevent consumer import shadowing, and Gitleaks also loaded the source-root
ignore file despite an alternate ignore path. The latter is avoided through a
private Git view of the same objects/index, without altering target files.

Repository policy's Python 3.15.1 interpreter was not available in this local
environment. Existing policy tests passed under 3.12.14; the existing hosted
policy lane retains 3.15.1, while the new Presidio lane explicitly uses its
qualified isolated 3.12 tooling environment.

Hosted publication, canary outcome and receiving-repository state are recorded
separately after they are observed. No repository deployment is claimed here.
