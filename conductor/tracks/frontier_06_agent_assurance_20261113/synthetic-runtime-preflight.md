# Synthetic runtime preflight — 27 November 2026

Refs #192. Distinct from #196, whose security-review hold and owned files
remain unchanged. No model inference or generated code is executed.
The candidate builds a fixed Docker dependency dry-run command, for a
caller-qualified digest-pinned local image and immutable private staged
wheelhouse. No pull, network, shell or arbitrary command; read-only root
and input bind, nonroot UID, all capabilities removed, no-new-privileges,
limited PIDs, 1 GiB RAM/swap total, 1 CPU, bounded temporary storage.
Require an independently pinned normalized requirements lock containing
exact package versions and SHA-256 hashes; reject URL/options, duplicate
names, symlinks, unknown wheel hashes and over-budget inventories. Native
pip resolves the transitive closure with no index, no source packages,
ignore-installed, require-hashes and dry-run.

Four focused source tests passed locally. The explicit
`python tests/synthetic_model_dependency_probe.py` canary executed native
pip 25.1.1 in an isolated Linux user/network namespace under Python 3.13.5.
Two deterministic synthetic wheels only: complete closure exit 0, missing
transitive hash exit 1, substituted digest exit 1; each exact expected
diagnostic was observed. No install, model execution or live conflict.
The actual Docker command is not executed in that probe. Docker is not
available locally; real filesystem, privilege, cgroup, timeout/cleanup
enforcement and image/runtime qualification remain open. Do not treat
argument shape as proof of isolation. Actual Hugging Face model dependency
closure, wheel provenance and separate #196 security review remain gated.
