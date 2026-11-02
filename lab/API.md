# Environnement audité : console Banque Kerlann (fictive)

Base URL : variable d'environnement `LAB_URL` (par défaut http://127.0.0.1:5050)

## Pages HTML (pour les captures de preuve)
- `/admin/security` : tableau des paramètres de sécurité
- `/admin/users` : comptes, e-mails, rôles, dernière IP, MFA par compte

## API JSON
- `GET /api/security` → objet :
  - `mfa_admin` (bool) : MFA exigé pour les administrateurs
  - `mfa_users` (bool) : MFA exigé pour les utilisateurs standards
  - `password_min_length` (int)
  - `password_require_complexity` (bool)
  - `lockout_threshold` (int, 0 = jamais de verrouillage)
  - `session_timeout_minutes` (int, 0 = jamais d'expiration)
  - `admin_audit_log` (bool)
- `PATCH /api/security` (corps JSON partiel, mêmes clés) → applique et renvoie l'objet complet
- `GET /api/users` → liste de `{login, email, role, last_ip, mfa}`
- `POST /api/reset` → remet l'état non conforme initial
