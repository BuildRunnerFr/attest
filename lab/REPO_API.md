# System under audit: source code repository `{repo}` (read-only gateway)

Base URL: environment variable `LAB_URL`. Every request needs the header `Authorization: Bearer <token>`;
tests run with the READ-ONLY audit token from the environment variable `LAB_TOKEN`.

## JSON API
- `GET /api/repo/{repo}/tree` → `{"repo": "{repo}", "files": ["app/config.py", ...]}` (paths relative to the repo root)
- `GET /api/repo/{repo}/file?path=<file>` → `{"path": "<file>", "lines": ["first line", ...]}` (line 1 is lines[0])
- `GET /api/repo/{repo}/search?q=<python regex>[&path_prefix=<dir/>]` → `{"matches": [{"path", "line", "text"}], "truncated": bool}`

## HTML pages (used as visual evidence)
- `/repo/{repo}/view?path=<file>`: the file with line numbers; each line is a table row.
  A test SHOULD return `"evidence_page": "/repo/{repo}/view?path=<file>"` for the file that best proves its result.

## Notes
- The repository is a Python service with `app/` (source), `tests/` (tests and fixtures), `requirements.txt`
  and a CI pipeline in `.github/workflows/`.
- There is no write interface: findings on code are remediated by the development team (manual remediation).
