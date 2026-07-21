# Security Policy

## Supported Versions

Security fixes are applied to the latest `0.2.x` release while the project is in beta.

## Reporting A Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub Private Vulnerability Reporting on this repository. If that control is temporarily unavailable, contact the repository owner privately through their GitHub profile. Include the affected version, reproduction steps, impact, and any suggested mitigation.

Maintainers will acknowledge a complete report as soon as practical, investigate it privately, and coordinate disclosure with the reporter. No response-time guarantee is made for this community project.

## Deployment Boundary

JWT signature, issuer, audience, expiry, and subject validation are built in and enabled by default. Deployers remain responsible for identity-provider configuration, secrets management, TLS, network controls, database access, authorization policy, tenant isolation, audit retention, and dependency updates. `AUTH_MODE=development` is only for local evaluation.
