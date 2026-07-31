# Solo-maintainer repository standard

- Zero required human approvals.
- No required CODEOWNERS review or team assignment.
- Block force-pushes and branch deletion.
- Require conversation resolution and only stable automated checks.
- Preserve an explicit owner recovery path.
- Use read-only workflow permissions by default and grant writes per job.
- Pin actions to immutable commits and update them with Renovate.
- Use a fast pull-request lane plus scheduled deep testing.
- Use Codecov OIDC for executable projects; coverage is not applicable to documentation-only, configuration-only, or empty repositories.