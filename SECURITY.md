# Security Policy

## Supported versions

Security fixes are applied to the latest released version of Planwise. Older versions are not patched.

| Version | Supported |
| ------- | --------- |
| latest  | yes       |
| older   | no        |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, report them privately through [GitHub private vulnerability reporting](https://github.com/anthonyverriest/planwise/security/advisories/new).

Include as much of the following as you can:

- A description of the issue and its impact.
- Steps to reproduce, or a proof-of-concept.
- The affected Planwise version(s) and environment.
- Any suggested mitigation or fix.

## What to expect

- Acknowledgement of your report within **5 business days**.
- An assessment and remediation plan within **10 business days**.
- Coordinated disclosure: we will agree on a public disclosure timeline with the reporter.
- Credit in the release notes for the fix, unless you prefer to remain anonymous.

## Scope

In scope:

- The `planwise` / `pw` CLI and its published packages.
- Workflow renderers and the directive IR.
- Official documentation and examples that could mislead users into insecure configurations.

Out of scope:

- Vulnerabilities in third-party dependencies (please report upstream).
- Issues requiring physical access to a developer's machine.
- Social engineering of project maintainers.
