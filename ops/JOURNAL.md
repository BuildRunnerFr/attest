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

## Cycle 1 de l'équipe d'agents — 4 novembre 2026, 00:15–01:00

Constats principaux (directeur d'audit, RSSI acheteur, coach de pitch, QA, designer) :
- RSSI : la garde statique se contournait (6 scripts sur 6 : lecture de /proc/<ppid>/environ → fuite de la clé,
  `getattr(requests,"pa"+"tch")`, `Session().send()`, `os.execv`, exfiltration par GET) ; piste d'audit réécrivable
  de bout en bout (chaîne sans clé) ; scripts promus en bibliothèque sans relecture ; capture non masquée envoyée au modèle.
- QA : une panne du modèle sur un seul contrôle faisait tomber l'audit (ni result.json ni manifest) ; `LAB_PORT` non
  transmis à l'auditeur ; Python 3.11+ non documenté ; requirements.txt non épinglé.
- Directeur d'audit : pré-approbations de démo comptées comme approbations humaines ; « RTS 21(3) » cité mais absent de
  la bibliothèque (controls/AUD-2026-IAM-01.en.json, politique PSI-4.7) — numérotation à vérifier par Ethan sur EUR-Lex ;
  `covered_by` affiché comme couverture totale ; opinion sans paragraphe de fondement ni réserve de périmètre.
- Coach : images du README en français et issues du mock (coût 0 $) ; chiffres non sourcés (« thirteen cents an audit »,
  « about 8 minutes, about $0.50 ») ; pas de texte de soumission, de LICENSE ni de script vidéo final.
- Designer : fuites de français en EN, preuves orphelines dans le PDF, écran d'audit du Studio peu hiérarchisé, 390 px.

Commit aab3076 (poussé sur main) :
- Bac à sable : garde statique renforcée + garde d'exécution (hook d'audit Python : GET seul, réseau vers la cible seule,
  ni fichier ni processus) ; secrets masqués dans les résultats et la piste (attest/redact.py) ; 5 des 6 contournements
  bloqués et testés (le 6e, renvoyer à la cible ce qu'on y lit, est inévitable et documenté).
- Une panne du modèle rend le contrôle non concluant (opinion avec réserve) ; rapport, result.json et manifest toujours émis.
- Les pré-approbations ne comptent plus comme approbations humaines ; libellés EN corrigés.
- SAM 3.1 : lots de 16 objets au plus. Docs : ARCHITECTURE, README et EVALUATION mis à jour. 72 tests verts.
- `demo-stable` NON mis à jour : le push forcé a été refusé par les garde-fous de la session (version sûre = aab3076).

Exécutions réelles :
- `20261103-232326-bench-meta` (main 9cc9dee) : 56/56, 0 FP, 0 FN, injection 1/1, 256/256 masquées dont 87 repérées
  par le modèle (178 au premier passage : rappel du modèle instable, verdicts stables), 0,53 $ mesuré, 300 s.
- `20261103-234658-code-meta` (aab3076) : 7/7 défauts, 0 erreur de preuve, aucun repli SAM (lots de 16 confirmés),
  aucun script refusé par la nouvelle garde ; 0,48 $ mesuré.
- `20261103-234915-iam-meta` (aab3076, EN, remédiation) : 6 non-conformités, 5 corrigées et re-testées conformes,
  opinion insuffisant → à améliorer ; 0,12 $ mesuré.
- Dépense cumulée au registre (estimation prudente) : 2,95 $ / 130 $.

Suite prévue : refaire les images du README en anglais à partir de `20261103-234915-iam-meta` ; texte de soumission,
script vidéo, LICENSE ; LAB_PORT / Python 3.11 / dépendances épinglées ; opinion avec fondement et réserve de périmètre,
`covered_by` en « partiellement couvert » ; ancrage de la piste (empreinte de tête au registre) ; bibliothèque de scripts
« non relus » ; correctifs d'affichage du designer.

## Premier audit réel dans GitHub Actions — 4 novembre 2026, 00:05

- Exécution `20261103-230340-code-meta` (workflow 41734972847, commit ab965ea) : audit du dépôt `paiement-api` par le
  Studio (RTS 16 + PDS-2), Muse Spark 1.3 + SAM 3.1.
- 7/7 défauts trouvés, chacun avec sa preuve : la correction de la preuve manquante de F-04 est confirmée.
  Interprétation : 20 exigences, 11 testées ici (7 règles + 4 clauses rattachées par `covered_by`), 9 en revue
  documentaire, 0 citation rejetée.
- Coût mesuré 0,33 $ (15 appels Muse Spark, 6 images SAM) ; 0,45 $ au registre (estimation prudente de SAM).
- Défaut révélé : « 17 objects exceed this model's limit of 16 » → SAM refuse plus de 16 boîtes par requête, et
  l'outil se rabat alors sur les boîtes du modèle. À corriger : découper en lots de 16 au plus (attest/sam.py).
- Verrou des cycles : `bash ops/cycle_lock.sh acquire|release` (branche `cycle-lock`). Version sûre pour la vidéo :
  branche `demo-stable` (les tags ne passent pas par le proxy des sessions).

## Point de départ — 4 novembre 2026, 00:00

- 30 tests verts ; CI `tests` verte ; lancement local en une commande (`bash scripts/start.sh`).
- Audits réels possibles sans le Mac d'Ethan : workflow `real-audit` (banc, IAM, code via le Studio, injection),
  résultats et dépense dans la branche `real-results`. Premier passage vérifié en mock.
- Derniers résultats réels (2 novembre) : banc 8 systèmes 56/56 justes, 0 faux constat, 0,65 $ ; audit de code par le
  Studio : 7/7 défauts trouvés, 0,30 $. Corrections du 3 novembre (preuve manquante de F-04, `covered_by`, cadrage des
  lignes de code) **pas encore confirmées avec les vrais modèles**.
- Réserves ouvertes : liste de mots génériques de PSI-4.7 (manque `ops`, `svc`, `it` ; contient des noms de famille
  comme `bureau`) ; backend local Muse Glimmer jamais testé sur du matériel réel (ne rien affirmer à son sujet).
