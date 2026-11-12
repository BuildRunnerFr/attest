# System under audit: HR register and application entitlements (Banque Kerlann — fictitious)

Read-only extract used to reconcile the HR register with the application accounts (joiners, movers, leavers).
Base URL: environment variable `LAB_URL`.

## Authentication
Every request needs the header `Authorization: Bearer <token>`.
Audit tests run with the READ-ONLY audit token, available in the environment variable `LAB_TOKEN`.

## HTML pages (used as visual evidence)
- `/lifecycle/reconciliation`: each account next to the HR record of its holder (or owner): account state, employee
  id, HR status, contract end, department, previous department and transfer date, last login, entitlements, last
  review. Use this page as evidence for rules that compare accounts with the HR register.
- `/lifecycle/accounts`: accounts with login, employee id (or owner), state, last login, entitlements, last review
- `/lifecycle/hr`: HR register with employee id, name, department, status, contract end, previous department, transfer date

## JSON API
All dates are ISO `YYYY-MM-DD`. Rules are evaluated at the reference date `as_of`, never at today's date.
- `GET /api/lifecycle/meta` → `{as_of, entity, employees, accounts}`; `as_of` is the reference date of the extract
- `GET /api/hr/employees` → list of
  `{employee_id, first_name, last_name, department, status, start_date, end_date, previous_department, transfer_date}`
  - `status`: `active` or `left`; `end_date`: last day of contract (null if none; may be today or in the future)
  - `previous_department`, `transfer_date`: set when the employee changed department (null otherwise)
- `GET /api/lifecycle/accounts` → list of
  `{login, email, type, employee_id, owner_employee_id, enabled, created, last_login, entitlements, last_access_review}`
  - `type`: `person` (belongs to `employee_id`) or `service` (no `employee_id`; responsible person in `owner_employee_id`)
  - `enabled` (bool): a disabled account gives no access
  - `last_login` (date or null), `created` (date)
  - `entitlements`: list of entitlement names; `last_access_review` (date or null): last access review of the account
- `GET /api/lifecycle/entitlements` → list of `{name, department, privileged}`; `department` is null for common
  entitlements; `privileged` (bool) marks privileged entitlements
