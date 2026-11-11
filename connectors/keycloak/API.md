# System under audit: Keycloak identity provider (test realm of a fictitious bank)

Keycloak is reached only through a READ-ONLY audit gateway. Base URL: environment variable `LAB_URL`.

## Authentication
Every request needs the header `Authorization: Bearer <token>`.
Audit tests run with the read-only audit token, available in the environment variable `LAB_TOKEN`.
The gateway only performs GET requests on Keycloak, with a service account limited to `view-realm` and `view-users`.

## HTML pages (used as visual evidence)
- `/kc/realm`: table of the realm security settings (one row per field below)
- `/kc/users`: user accounts with username, e-mail, realm role, enabled, MFA status (100 per page)
- `/kc/roles/admin/users`: only the accounts holding the realm role `admin`

## JSON API (fields are those of the Keycloak Admin REST API)
- `GET /api/kc/realm` → object (realm representation, security fields only):
  - `passwordPolicy` (string or null): policies joined by ` and `, e.g. `length(12) and upperCase(1) and digits(1)`;
    null or missing item = no such requirement. Items: `length`, `upperCase`, `lowerCase`, `digits`, `specialChars`
  - `bruteForceProtected` (bool): account lockout on repeated login failures is enabled
  - `failureFactor` (int): number of login failures before lockout (only applies if `bruteForceProtected`)
  - `ssoSessionIdleTimeout` (int, seconds): idle time after which a session expires
  - `ssoSessionMaxLifespan` (int, seconds)
  - `adminEventsEnabled` (bool): administration actions are recorded as admin events
  - `adminEventsDetailsEnabled` (bool), `eventsEnabled` (bool): login events are recorded
  - other fields: `realm`, `enabled`, `permanentLockout`, `registrationAllowed`, `rememberMe`, `sslRequired`
- `GET /api/kc/users?first=<offset>&max=<n>` → list of `{id, username, email, firstName, lastName, enabled, totp}`.
  `totp` (bool): the account has an OTP credential configured (multi-factor authentication); an account with
  `totp: false` signs in with a password only.
- `GET /api/kc/users/count` → `{count}`
- `GET /api/kc/roles` → list of realm role names
- `GET /api/kc/roles/{role}/users?first=<offset>&max=<n>` → accounts holding that realm role (same fields).
  Privileged (administrator) accounts are the members of the realm role `admin`.

## Not available to audit tests
Any write to Keycloak (the gateway has no write route and its service account is read-only).
