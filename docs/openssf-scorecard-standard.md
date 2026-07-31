# OpenSSF Scorecard standard

Scorecard is required for public repositories with `published` or `high_risk`
supply-chain profiles. It is also appropriate for the public
`repository-standards` control plane because consumers rely on its workflows.

For private repositories, Scorecard is optional evidence-only automation. Its
results must not be published, and the additional token needed for some checks
must be justified against the information gained.

The numeric score is diagnostic, not a release gate. In particular, this estate
retains zero mandatory human approvals and does not add a second developer,
CODEOWNERS dependency, or manual approval solely to increase the
Branch-Protection score.

The managed workflow:

- uses current, resolvable immutable action pins;
- has read-only defaults and narrow SARIF/OIDC job permissions;
- disables persisted checkout credentials;
- runs weekly and on relevant default-branch/protection changes;
- uploads SARIF to GitHub code scanning and retains a bounded artifact;
- publishes results only for repositories explicitly classified as public and
  applicable;
- adds a badge only after a real published Scorecard result is verified.

Rollout follows the normal sequence: central canary, archetype canaries,
impact simulation, bounded managed pull requests, stable checks, then
low-risk automerge with zero human approvals.
