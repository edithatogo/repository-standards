# Optional FAIR research software profile

This is an **opt-in, advisory** repository standard, not a new mandatory compliance or release requirement.

## Scope and decision

See [the machine-readable policy](../profiles/fair-research-software.json).
Adopt for active, canonical, public research libraries, reusable scientific methods, and independently published scientific software where maintainers select `fair_software.enabled: true` in the registry. Applications, research datasets and workflows require case-by-case classification. Private, archived, fork-only, documentation-only and operational repositories are excluded by default. Missing declarations mean **disabled**. Do not auto-rollout or promote a repository based solely on name or a badge.

## Minimum evidence when opted in

1. Verify a specific published commit and repository identity. Use the existing howfairis action, pinned to upstream `4c11146488125aa6e1531184eed51d781bcd5871` (v0.2.1), with `contents: read`, advisory operation and an actual hosted-run receipt. The checker uses public repository metadata; PR results may reflect the default branch.
2. Record observed five-part results separately for public source, recognized license, verified registry, citation metadata and software quality checklist. **Unknown is not pass.**
3. Carry out the [ARDC FAIR checklist](https://github.com/ardc-fair-checklist/ardc-fair-checklist.github.io) as a separate evidence-backed manual assessment, not as a claimed automated check.
4. Review code/data rights, external authors, identifiers, `CITATION.cff`, reproducible fixtures and releases. Do not generate a license, DOI, registry record, badge or citation claims merely to increase a score.
5. Preserve independent scientific, security, data rights and release qualification, as well as existing Conductor ownership and holds.

## Ponytail application

Use [Ponytail's reuse-first ladder](https://github.com/DietrichGebert/ponytail): reuse existing workflows, documentation and scanners before implementing new tooling. Keep changes narrow and test material logic. Do **not** install Ponytail, create a new agent layer, or replace native workflows just to support this optional control.

## Rollout disposition

The first 18 candidates have **draft PRs, not accepted FAIR status**. Further candidates from the scientific-native capability map include `innovate` and `mars`; assess for duplicate checks and release boundaries before opting in. Additional candidates include `NationalWeightedActivityUnitWrapper.jl`, `Syspop`, `populationsim`, `lifetimes`, and research simulation projects. Ownership, support status and live readiness require validation.

Track per-repo eligibility, whether opted in, exact head, hosted run, evidence document, ARDC results and gaps. Existing required checks are not to be weakened. Avoid adding a managed file or mandatory policy gate until pilot execution is validated.

Sources: [howfairis](https://github.com/fair-software/howfairis), [howfairis action](https://github.com/fair-software/howfairis-github-action), [ARDC](https://github.com/ardc-fair-checklist/ardc-fair-checklist.github.io), [Ponytail](https://github.com/DietrichGebert/ponytail).
