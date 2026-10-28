# Workflow

Use isolated branches and one writer per checkout. Record owned paths and the
integration handoff. Write failing behavioral tests before code, implement,
then run focused checks and the complete policy suite at a coherent milestone.

Validation: `PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v`.
Verify the repo-local interpreter is Python 3.15.1. Preserve failures. Agent
correctness/security review replaces independent human-owner requirements.
Commit only owned files with normal hooks; open a PR and require hosted checks.
No policy deployment, repository activation or scientific acceptance is implied
by a profile declaration. Complete and archive only after all linked gates pass.
