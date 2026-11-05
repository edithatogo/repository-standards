# Scientific/native qualification

The approved cohort and directed ownership graph live in
[the scientific profile](../profiles/scientific-native.json). This profile is
additive: it does not silently reassign existing repository archetypes, replace
local tests, activate rulesets or certify scientific runtime behavior.

Use the repo-local Python 3.15.1 interpreter:

```sh
.venv/bin/python scripts/scientific_ecosystem.py policy profiles/scientific-native.json
.venv/bin/python scripts/scientific_ecosystem.py candidate candidate.json
.venv/bin/python scripts/scientific_ecosystem.py receipt resource-receipt.json
PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v
```

Candidate records bind candidate identity, exact source revision, status and
security/build/numerical/consumer/resource checks. A qualified candidate requires
all five passes. A blocked candidate records blocker, affected capability, owner
and revisit condition. Candidates include releases, prereleases and pinned
nightlies; no automatic preference for obsolete support floors is implied.

Resource receipts distinguish runtime-build, compiler-bootstrap, hpc-install and
scheduler-run. Record exact source hashes, toolchain identities, argv, runner,
cache state, concurrency, times, terminal exit/stop state, descendant RSS or
cgroup peak, disk growth, intervals and measurement limitations. Missing counters
are not zero. Failed or partial jobs remain retained, never promoted to passes.
Historical process-group samples remain historical evidence and must not be
relabelled descendant measurements. Compiler bootstrap receipts additionally
identify the packaging requirement, binary bootstrap and source-built components.

Validation checks completeness and internal consistency; it cannot authenticate
producer claims. Consumers must independently verify artifacts, source hashes,
actual output, installed identities and relevant numerical/ABI contracts before
acceptance. The existing verification receipt remains the overall gate summary;
resource receipts are separate evidence artifacts referenced by its SHA256.

Keep core, bindings, backend, build-only, test-oracle and development dependencies
separate. Arrow Rust, PyArrow and Polars versions are independent release lines;
qualify interchange and buffer ownership rather than matching version strings.
Do not add Python/GPU/plotting to a native core to share a policy file.

Use compiler timing and resource observations to identify costly stages before
CPU flamegraph/perf or DHAT/heap allocation investigations. SDK-based runtime
builds never prove a compiler-from-source or full HPC matrix gate. The Voiage HPC
track remains a delivery dependency; requirements may be revised only explicitly.


## Focused testing and native dataframe boundaries

Repository owners must declare affected test selectors and preserve full milestone gates for dependency, packaging, shared-fixture and integration changes. Reverse-import selection is an optimization, not proof of dynamic plugin coverage. Unknown impact requires explicit integration selectors or a complete milestone. Keep pytest cacheprovider enabled; an empty failure cache does not verify tests. Zero retries is the default.

For repositories declaring a native Polars boundary, distinguish production source, test oracles and legacy scripts. Enforce imports and conversion boundaries with regression checks and a pandas-absent installed-package replay. Do not claim the whole repository is pandas-free while development or script consumers remain. Preserve numerical predicates, error/presence semantics and immutable oracles during migration.

Qualify optional test tools on the actual repo-local Python 3.15.1 interpreter. Hypothesis requires meaningful invariants; mutation reports require exact targets and surviving/killed/error dispositions. Dead-code findings require review of public keyword and dynamic entry-point compatibility. Network denial and bounded timeouts belong to qualified local unit workloads; they must not silently interrupt native mutations. Parallelism and randomized order require fixture isolation and reproducible RNG contracts before adoption. Prefer one authoritative development dependency group, with separate optional consumer roles, rather than overlapping tool lists.

Distinguish an explicit performance requirement, a hang timeout and a property-generator timing heuristic. Retain correctness predicates and explicit hang bounds under coverage/mutation instrumentation. Preserve heuristic timing failures and their explanation; do not conceal them with retries or describe them as numerical defects. A small mutation target proves only the generated operators and exercised consumers recorded in its receipt.

## Package and automation identity

SCM-derived versions require full checkout history and tags in build jobs. Runtime version reporting should read installed distribution metadata. Qualify any source-archive fallback explicitly; a fallback version does not prove release/tag identity. Pin build tools and verify the actual wheel built from the source distribution.

Source-only releases require an explicit payload allowlist, exact packaged-source comparisons, a complete licence check, typing markers where applicable and consistent version/runtime metadata. Exclude workbooks, datasets, manuscripts, notebooks and private coordination/evidence when they are outside publication authority. Keep input qualification and privacy screening separate from archive path checks. An installed-package replay remains separate from an editable-environment test run.

Pin automation actions/hooks to reviewed immutable revisions and retain updater support for those pins. A successful Renovate extraction or configuration validator does not prove the hosted bot updated the lock, and Codecov YAML validation does not prove upload processing or delivery of the required coverage statuses. Record exact local runtime/tool versions and unresolved native-module fallbacks rather than modifying another owner's shared installation.

## Logging and security boundaries

Library diagnostics use module logging; application entry points own root logging configuration. Do not log credentials or raw secret configuration/validation payloads. Authentication adapters must deny when no trusted credential verifier is supplied, revoke stale principals on failed switches and retain separate web/session integration qualification. Sensitive configuration needs authenticated encryption and explicit key custody/migration; a reversible encoding is not encryption. Preserve existing files and keys until migration is authorized and verified.
