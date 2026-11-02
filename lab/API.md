# System under audit: KRL-ADM (Banque Kerlann IAM admin console — fictitious)

Base URL: environment variable `LAB_URL` (default http://127.0.0.1:5050)

## Authentication
Every request needs the header `Authorization: Bearer <token>`.
Audit tests run with the READ-ONLY audit token, available in the environment variable `LAB_TOKEN`.
The read-only token cannot modify anything (HTTP 403).

## HTML pages (used as visual evidence)
- `/admin/security`: table of security settings
- `/admin/users`: accounts with login, e-mail, role, last IP, MFA status
- `/admin/journal`: change log (ticket, account, approver, changes)

## JSON API
- `GET /api/security` → object:
  - `mfa_admin` (bool): MFA required for privileged (admin) accounts
  - `mfa_users` (bool): MFA required for standard users
  - `password_min_length` (int)
  - `password_require_complexity` (bool)
  - `lockout_threshold` (int, 0 = never locks)
  - `session_timeout_minutes` (int, 0 = never expires)
  - `admin_audit_log` (bool): administration actions are logged
- `GET /api/users` → list of `{login, email, role, last_ip, mfa}`; `role` is `admin` or `conseiller`
- `GET /api/journal` → list of `{ts, ticket, actor, approved_by, changes}`

## Change interface (NOT available to audit tests)
- `PATCH /api/security` with a partial JSON body (same keys). Requires the change-account token and the
  headers `X-Change-Ticket` and `X-Approved-By`. Every change is written to the journal.
