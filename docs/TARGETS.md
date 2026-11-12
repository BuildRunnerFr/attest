# Beyond the demo console: a real Keycloak, and HR ↔ access reconciliation

The headline benchmark audits a console written for Attest. Two more targets answer the obvious objections:
*does it work on software it has never seen?* and *can it do a real audit task, not just read seven settings?*
Every figure below comes from a run stored in the [`real-results`](../../../tree/real-results) branch (run id given).

## 1. Keycloak (open-source identity provider)

```
Attest test script ──GET──▶ read-only gateway ──GET──▶ Keycloak Admin REST API
 (audit token)              connectors/keycloak        (service account: view-realm, view-users)
```

- **Real software.** Keycloak 26.0.5 runs in Docker (or from a local install); `connectors/keycloak/seed.py` loads three
  fictitious realms (260, 243 and 180 synthetic accounts) with planted flaws and a ground truth for policy PSI-4.
- **Read-only by construction.** The gateway has no write route and only issues GET requests. Its service account
  holds `view-realm` and `view-users` on the audited realms and nothing else: a write returns HTTP 403 from Keycloak
  itself. The bootstrap admin password and the audit secret are random at each start; the gateway never sees the
  bootstrap account or the model API key.
- **Data minimisation.** The gateway returns only security-relevant fields (no SMTP or federation settings, no
  credentials), and serves read-only HTML pages used as visual evidence.
- **A real trap.** Keycloak returns 100 users per call by default. The gateway declares that pagination with standard
  headers (`Link rel="next"`, `X-Total-Count`); Attest refuses a "compliant" verdict concluded on a partial read.
  In realm `kerlann`, the only generic administrator (`support-n2`) is beyond the first 200 accounts.

Run it:

```bash
bash ops/keycloak_up.sh                          # Keycloak + realms + gateway on http://127.0.0.1:5050
python -m attest run mission/keycloak.toml       # one audit of realm kerlann
python -m attest bench --target keycloak         # the 3 realms against the ground truth
```

Results with Muse Spark 1.3 + SAM 3.1 on a real Keycloak (GitHub-hosted runner):

| Run | Checks correct | Missed | False findings | Inconclusive | Offending accounts named | Cost |
|---|---|---|---|---|---|---|
| `20261111-121909-keycloak-bench-meta` (first ever) | 19 / 21 | 0 | 1 | 1 | — | $0.72 |
| `20261112-130651-keycloak-bench-meta` | **21 / 21** | 0 | 0 | 0 | 270 / 270, precision 100 % | $0.66 |

What changed between the two, stated plainly:
- The "false finding" of the first run was **an error in our ground truth, not in the agent**. Attest reported the one
  administrator without MFA under PSI-4.2 ("MFA for users") as well as PSI-4.1; our oracle had excluded
  administrators from "users". An administrator is a user: the oracle was corrected, the agent was not changed for it.
- The inconclusive check was a script that flagged a compliant administrator (hyphenated first name); the visual
  cross-check refused to corroborate it, so it ended "needs review" instead of becoming a false finding. In the second
  run the regenerated script (whole-token rule added to the script prompt on 11 Nov) did not flag it.
- Three realms and two runs are a small sample: this shows the approach carries over to real software, not a
  production accuracy figure.

The work programme and the seven scripts of the second run are in `controls/AUD-2026-KC-01.en.json` and
`library/PSI-4.*` (not yet reviewed by a human auditor). `tests/test_keycloak.py` replays them without any model against
the ground truth of the three realms, through the real gateway in front of a small Keycloak stub.

## 2. Access lifecycle: HR register ↔ accounts (joiners, movers, leavers)

Target `iam-lifecycle` serves, read-only and paginated, an HR register, the application accounts with their
entitlements, and the entitlement catalogue (`lab/LIFECYCLE_API.md`). Policy PSI-5 sets six rules; each one requires
joining at least two sources at a reference date:

| Rule | What Attest has to establish |
|---|---|
| PSI-5.1 | an enabled account whose holder's contract ended before the reference date (leaver) |
| PSI-5.2 | an enabled account with no known holder, or a service account whose owner left (orphan) |
| PSI-5.3 | an enabled personal account with no login for more than 90 days (dormant) |
| PSI-5.4 | one account holding both sides of a sensitive pair, e.g. payment entry + payment validation (segregation of duties) |
| PSI-5.5 | rights of the previous department still held more than 30 days after a transfer (mover) |
| PSI-5.6 | a privileged entitlement not reviewed for more than 365 days |

Three synthetic scenarios (430, 380 and 250 employees, generated from fixed seeds). Each planted case has a
near-miss twin that must be judged compliant: contract ending today, 90 and 365 days exactly, transfer 30 days ago,
offending but disabled accounts, two unrelated sensitive rights. In the third scenario the only two offenders are
outside the first page of 100.

```bash
python -m lab.app                                  # the demo console also serves this target
python -m attest run mission/lifecycle.toml
python -m attest bench --target iam-lifecycle
```

| Run | Checks correct | Missed | False findings | Inconclusive | Offending accounts named | Cost |
|---|---|---|---|---|---|---|
| `20261111-123208-lifecycle-bench-meta` (first ever) | 14 / 18 | 0 | 1 | 3 | 17 / 17, precision 81 % | $0.99 |
| `20261112-125816-lifecycle-bench-meta` | **17 / 18** | 0 | 0 | 1 | 17 / 17, precision 100 % | $0.77 |

What the first run showed, and what was changed:
- **A false finding from double counting.** A leaver's account (PSI-5.1) was also reported as an orphan (PSI-5.2). The
  policy now states that a holder who is in the register but has left falls under PSI-5.1 only.
- **Pages read twice.** The scripts followed `Link rel="next"` and also looped on `X-Total-Pages`, so accounts were
  counted twice (hence the 81 % precision on named accounts). The script prompt now imposes one pagination mechanism
  and one count per item.
- **Compliant checks stuck at "needs review".** The evidence page listed accounts without the HR columns, so the visual
  cross-check could not confirm a join. A reconciliation page now shows each account next to its holder's HR record.
- The remaining inconclusive check is a compliant mover rule: the screenshot is page 1 of 4 and the cross-check
  refused to confirm from one page. Since then the cross-check is told when a screenshot is one page of a paginated
  list (see `ops/JOURNAL.md` for the re-measurement).

The work programme and six scripts of the second run are in `controls/AUD-2026-JML-01.en.json` and `library/PSI-5.*`
(not yet reviewed by a human auditor); `tests/test_lifecycle.py` replays them without any model and checks that they
name exactly the expected accounts in the three scenarios.

## Honest limits

- Keycloak is audited on realm settings and accounts only: clients, identity federation and custom authentication
  flows are out of scope, and "MFA" means "an OTP credential is configured", as the API exposes it.
- The lifecycle data is clean by design (ISO dates, one identifier per person). Real HR extracts are messier:
  duplicated identities, name changes, several source systems.
- None of these targets is remediated by Attest: disabling a leaver's account or removing a right is the owner's
  decision, so findings become an action plan.
