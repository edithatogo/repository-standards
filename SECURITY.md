# Security policy

## Supported versions

Follow the affected repository's README, release notes and local security policy
for its supported versions and maintenance status. This shared policy does not
declare every repository or historical release actively supported. If no support
window is published, include the affected version or commit in the report and
ask the maintainer to confirm its status.

## Reporting a vulnerability

Report a suspected vulnerability to the **affected repository**, using its
**Security** (or **Security and quality**) tab and **Report a vulnerability**
when that option is available. Read any repository-specific reporting guidance
shown there before submitting. A `SECURITY.md` file does not by itself enable
GitHub private vulnerability reporting.

If private reporting is unavailable, follow any verified private contact listed
by that repository. If no such contact is published, open an issue requesting a
preferred security contact **without including the vulnerability description,
affected component, proof of concept, logs or sensitive attachments**. A suitable
request is: "Please provide a private contact route for a security report."
Wait for a private channel before sharing details. Do not use the `.github`
repository's advisory form for another project unless the maintainer directs
you there.

This follows GitHub's guidance on
[private reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/report-privately)
and [coordinated disclosure](https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/coordinated-disclosure).

## What to include

In the private report, provide the repository and affected version/commit, a
clear description of the impact, minimal safe reproduction steps and the
environment needed to reproduce it. Distinguish observed effects from
assumptions. Use synthetic data where possible and redact credentials, personal
information and unrelated source records. State whether you have a proposed fix
or need help establishing a safe reproduction.

## Response and disclosure

The sole maintainer reviews reports as capacity permits; there is no guaranteed
response or remediation time. The maintainer may request further evidence,
confirm affected versions, coordinate a fix and agree on disclosure through the
private thread. Keep vulnerability details private while that discussion is
under way. Security decisions use the required automated checks and evidence;
they do not require a second human approver.

If credentials have been exposed, their owner should revoke or rotate them
through the relevant service promptly. Deleting a public post or commit is not
a substitute for revocation. Do not test against systems or data without the
owner's authorisation.
