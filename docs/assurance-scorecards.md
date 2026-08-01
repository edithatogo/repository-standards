# Assurance scorecards and attestations

## Security Insights

Maintained public published/high-risk repositories should carry a validated
`security-insights.yml`. It is a machine-readable snapshot, not proof that all
claims are current; consumers must bind it to the commit or release that ships
it. Repository-specific facts override inherited defaults.

## SLSA

Published artifacts should carry verifiable provenance. SLSA verification is a
release-consumption gate: it checks the artifact, provenance statement, source
URI and trusted builder identity. It complements, but is stronger than, a
Scorecard provenance check.

## OpenSSF Best Practices Badge

Pilot only on mature public canonical repositories. The badge is partly
self-attested and must not be copied into READMEs before the project has
completed the questionnaire with evidence. It is not required for every
single-developer repository.

## Criticality Score

Use OpenSSF Criticality Score as an internal prioritisation input, never as a
quality or security grade. It can raise the review tier for repositories with
high external influence, but it cannot lower controls for a low-scoring private
repository. Running the upstream collector may require GCP/BigQuery access;
that credential boundary remains explicit.

## Non-goals

CLOMonitor, Allstar and Minder are not added as concurrent estate writers at
this stage. They may be evaluated after the GitHub App and managed-remediation
canaries are operational, with one authoritative policy writer retained.
