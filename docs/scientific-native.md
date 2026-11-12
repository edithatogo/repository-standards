# Scientific/native qualification

The approved cohort and directed ownership graph live in [the scientific profile](../profiles/scientific-native.json). This profile is additive: it does not silently change repository archetypes, activate rulesets, replace numerical tests or certify runtime behaviour.

The 7 November 2026 [innovation ecosystem update](innovation-ecosystem-boundaries.md) makes Innovate's Rust-core/Polars direction mandatory, retires pandas/xarray support in the new release, records VOP as a proof of concept with Voiage-owned generic methods, and consolidates game-runtime ownership. Existing exact-source evidence remains historical evidence; consumer migrations require their own acceptance.

Use the repo-local qualified interpreter. Python 3.15.2 is the new interface/tooling candidate; source execution and installed consumers must be requalified rather than relabelling older receipts:

```sh
python scripts/scientific_ecosystem.py policy profiles/scientific-native.json
python scripts/scientific_ecosystem.py candidate candidate.json
python scripts/scientific_ecosystem.py receipt resource-receipt.json
PYTHONPATH=scripts python -m unittest discover -s tests -v
```

Candidate records bind identity, exact revision and security/build/numerical/consumer/resource checks. A qualified candidate requires all five passes. A blocked candidate records blocker, affected capability, owner and revisit condition. Releases, prereleases and pinned nightlies may be candidates; no preference for obsolete floors or unqualified upgrades is implied.

Resource receipts distinguish runtime-build, compiler-bootstrap, hpc-install and scheduler-run. Record exact source hashes, toolchain, argv, runner/cache state, concurrency, timestamps, terminal exit/stop state, descendant RSS or cgroup peak, disk growth, measurement interval and limitations. Missing counters are not zero; failed/partial jobs do not pass. Historical process-group samples are not relabelled descendant measurements. Compiler bootstrap records identify the packaging requirement, binary bootstrap and source-built components.

Structural validation cannot authenticate producer claims. Consumers independently verify artefacts, hashes, actual outputs and relevant numerical/ABI contracts. The existing verification receipt remains the overall summary; resource evidence is referenced by SHA-256.

Separate core, binding, backend, build-only, isolated test-oracle and development dependencies. Arrow Rust, PyArrow and Polars versions are independent release lines: qualify schema/buffer/lifetime interchange. No Python/GPU/plotting dependency belongs in a minimal native core solely to share a policy file. The current Kairos Git-Polars/root-patch and packaging constraints are documented in the linked boundary update.

Profile compiler timings/resources before optimisation. An SDK runtime build never proves compiler-from-source or full HPC acceptance. Existing Voiage HPC requirements remain open until explicitly changed and qualified; this policy does not waive them.
