# Journal d'amélioration continue

Tenu par les sessions planifiées (équipe d'agents). Une entrée par cycle, la plus récente en haut :
constats de l'équipe, changements poussés (commits), exécutions réelles (id du registre, coût, résultat),
suite prévue. Les chiffres cités viennent tous de `ledger.jsonl` (branche `real-results`) ou de `examples/`.

## Règles fixées par Ethan (à respecter à chaque cycle)

- Données 100 % synthétiques : aucune donnée personnelle, aucune donnée ni mention d'employeur réel ; pas de métier
  ni d'e-mail personnel d'Ethan dans le dépôt. Commits : `Ethan Blombou <289934308+BuildRunnerFr@users.noreply.github.com>`.
- La clé de l'API n'est jamais affichée, journalisée ni versionnée (secret GitHub `MODEL_API_KEY`).
- `"reviewed": true` dans `controls/` est une validation humaine : seul Ethan la donne.
- Plafond des appels aux modèles Meta : 130 $ cumulés (estimation prudente du registre) ; au-delà, plus d'exécution réelle.
- Gel du code le 4 novembre 2026 à 18:00 (Paris) : ensuite, documentation, texte de soumission et vérifications
  seulement. Soumission : 5 novembre 2026, 03:00 (Paris) = 4 novembre 21:00 (ET).

## Point de départ — 4 novembre 2026, 00:00

- 30 tests verts ; CI `tests` verte ; lancement local en une commande (`bash scripts/start.sh`).
- Audits réels possibles sans le Mac d'Ethan : workflow `real-audit` (banc, IAM, code via le Studio, injection),
  résultats et dépense dans la branche `real-results`. Premier passage vérifié en mock.
- Derniers résultats réels (2 novembre) : banc 8 systèmes 56/56 justes, 0 faux constat, 0,65 $ ; audit de code par le
  Studio : 7/7 défauts trouvés, 0,30 $. Corrections du 3 novembre (preuve manquante de F-04, `covered_by`, cadrage des
  lignes de code) **pas encore confirmées avec les vrais modèles**.
- Réserves ouvertes : liste de mots génériques de PSI-4.7 (manque `ops`, `svc`, `it` ; contient des noms de famille
  comme `bureau`) ; backend local Muse Glimmer jamais testé sur du matériel réel (ne rien affirmer à son sujet).
