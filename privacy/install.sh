#!/usr/bin/env bash
# Build the scanner in an isolated, hash-locked Python 3.15.1 environment.
set -euo pipefail
umask 077
if [[ "$#" != 2 ]]; then
  echo 'Usage: privacy/install.sh ABSOLUTE_PYTHON_3_15_1 DESTINATION' >&2
  exit 2
fi
python="$1"
destination="$2"
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
"$python" -I -c 'import sys; assert sys.version_info[:3] == (3, 15, 1), sys.version'
if [[ -e "$destination" ]]; then
  echo 'Choose a new directory for the isolated scanner' >&2
  exit 2
fi
mkdir -p -- "$destination"
uv venv --python "$python" "$destination/venv"
runtime="$destination/venv/bin/python"
uv venv --python "$python" "$destination/build"
builder="$destination/build/bin/python"
uv pip install --python "$builder" --require-hashes --only-binary=:all: \
  -r "$root/privacy/build-requirements.lock"
"$builder" -I "$root/scripts/build_privacy_wheels.py" --destination "$destination/wheels"
"$runtime" -I - "$destination/wheels" <<'PY' > "$destination/wheels.lock"
from hashlib import file_digest
from pathlib import Path
from sys import argv

wheel_dir = Path(argv[1]).resolve()
names = ("presidio_analyzer-2.2.366+python315.1-", "presidio_anonymizer-2.2.366+python315.1-", "pyyaml-6.0.3-")
wheels = sorted(wheel_dir.glob("*.whl"))
if len(wheels) != len(names) or any(sum(p.name.startswith(n) for p in wheels) != 1 for n in names):
    raise SystemExit("Privacy wheel inventory mismatch")
for path in wheels:
    with path.open("rb") as wheel:
        digest = file_digest(wheel, "sha256").hexdigest()
    print(f"{path.as_uri()} --hash=sha256:{digest}")
PY
uv pip install --python "$runtime" --require-hashes --only-binary=:all: \
  -r "$root/privacy/requirements.lock" -r "$destination/wheels.lock"
uv pip check --python "$runtime"
"$runtime" -I "$root/scripts/install_gitleaks.py" --destination "$destination/bin"
