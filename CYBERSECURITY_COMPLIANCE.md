# Cybersecurity and Compliance Plan

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

## Authentication

- All authenticated clinical views are protected by Django login and role checks.
- Role-aware navigation limits what users see by default.
- Session-based access is used for the prototype environment.

## Access Control

- Role-based access control is enforced through application views and groups.
- Administrative and clinical areas are separated by module and permission context.
- Sensitive actions should remain audit logged and attributable to a named user.

## Audit Logging

- The system records key actions through the application audit trail pattern.
- High-risk workflows such as medication, results review, admission, and billing should remain traceable.

## Data Protection

- The prototype is designed around synthetic data only.
- PHI should be protected through least-privilege access and secure deployment settings.
- Transport security, secret management, and storage encryption are deployment responsibilities.

## Incident Response

- Security incidents should be triaged by severity.
- Immediate actions: isolate affected accounts, preserve logs, and stop unsafe access.
- Recovery actions: reset credentials, review access history, and validate data integrity.

## Backup and Recovery

- The deployment model should include regular database backups.
- Recovery procedures should be tested before real-world use.
- Offline or queued actions should be reviewed for consistency after reconnect or restore.

## Legal and Ethical Considerations

- Use only synthetic or fictional patient data in the challenge submission.
- Respect the joint IP and branding requirements in the brief.
- Ensure access, retention, and disclosure policies align with institutional and national governance.
