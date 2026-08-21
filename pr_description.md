🎯 **What:** Fixed a command injection vulnerability in `.github/workflows/managed-remediation.yml` where a workflow input was directly interpolated into a bash script execution.

⚠️ **Risk:** If a malicious actor could control or influence the `candidate_limit` workflow input, they could inject arbitrary bash commands into the `Simulate and plan` step, potentially gaining unauthorized access or executing unintended commands within the runner's environment.

🛡️ **Solution:** Passed the untrusted `${{ inputs.candidate_limit }}` input securely as an environment variable (`CANDIDATE_LIMIT`) and referenced it as a standard bash variable (`"$CANDIDATE_LIMIT"`) inside the `run` script, mitigating the injection risk.
