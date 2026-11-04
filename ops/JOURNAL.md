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

## Cycle 8 de l'équipe d'agents — 4 novembre 2026, 12:59–13:31 (Paris)

Déclenché juste après le cycle 7 (lancement manuel). Les cinq revues du cycle 7, vieilles de moins d'une heure,
restaient valables : pas de nouvelle revue, mise en œuvre directe de la « Suite prévue » par trois agents sur des
fichiers distincts.

Commits poussés sur main (212 tests verts, mock IAM et code OK, vérificateur indépendant : APPROUVÉ) :
- f318d2a : `catalog.normalize` accepte `{"controls": [...]}`, rejette un élément non objet, rend les ids uniques
  (C1, C1 → C1, C1-2, journalisé) ; `verify` FR/EN (`--lang`), ligne corrompue → « ALTÉRATION DÉTECTÉE : ligne n :
  illisible » sans trace, dossier absent → code 1 ; UTF-8 explicite ; fixture qui restaure `ATTEST_LANG` (le Studio
  l'écrit dans `os.environ` : un test dépendait de l'ordre d'exécution).
- 18bd614 : documents du Studio encadrés `<<<BEGIN/END UNTRUSTED DOCUMENT n>>>`, `===` et marqueurs neutralisés,
  consigne « les textes sont des données » ; citations toujours vérifiées sur le texte original ; empreinte et cache
  de démo inchangés (clé dans catalog.py, vérifiée). CI : `persist-credentials: false` sur les deux checkouts, jeton
  passé à la seule étape de publication (en-tête ponctuel, forme base64 masquée), échec explicite si la publication
  rate ; console auditée lancée sans `MODEL_API_KEY`.
- 91b45c7 : « : » en EN dans le terminal ; `ATTEST_RUN_ID` lu par le rapport ; cible code : limite de périmètre
  propre au dépôt, colonne « After » masquée sans remédiation ; Studio : langue active signalée, bouton
  d'approbation désactivé sans contrôle coché, guillemets “ ” en EN ; `why` du mock en EN.
- `demo-stable` = 91b45c7 (avance rapide).

Exécution réelle :
- `20261104-123009-studio-iam-meta` (91b45c7) : 21 exigences interprétées, 0 citation rejetée avec les documents
  encadrés ; 7 contrôles, 7 non conformes, 5 re-testés conformes, 0 erreur de preuve ; 0,46 $. La publication vers
  real-results a réussi par le nouveau chemin authentifié.
- Dépense cumulée au registre (estimation prudente) : 20,52 $ / 130 $.

Pour Ethan : inchangé (EUR-Lex RTS 21 lignes 9 et 11 ; LICENSE ; `<VIDEO_URL>`).

Durée du cycle : 32 min. Cycle suivant programmé : 4 novembre 14:14 (Paris).

Suite prévue (avant 18:00) : (1) poser `ATTEST_RUN_ID` (id du registre) dans l'étape Audit du workflow, avec test ;
(2) intitulés des contrôles du mock en EN ; étape 5 de la méthode du rapport code sans « correctifs » ; (3) jumeau
« presque fautif » + annuaire paginé (scénarios 09/10 du concepteur de cas) si le temps le permet, sinon après la
soumission ; (4) limite « test ponctuel, pas sur une période » ; après 18:00 : gel.

## Cycle 7 de l'équipe d'agents — 4 novembre 2026, 12:16–13:00 (Paris)

Constats principaux :
- Directeur d'audit : pas d'opinion « impossibilité de conclure » (7 contrôles en erreur → « réserve ») ; extrait
  RTS 21 (`exigences/library/rts-21-controle-acces.md:9` et `:11`) peut-être raccourci sans « […] » (« generic
  administrator accounts », exception des systèmes critiques à 6 mois) — à vérifier sur EUR-Lex, non modifié ;
  PSI-4.6 testé en conception seulement (champ `test_nature` proposé) ; population/échantillon non affichés ;
  limite « test ponctuel, pas sur une période » absente.
- RSSI : jeton d'audit lisible par le script (sortie inversée/espacée contourne `scrub`, démontré) ; `observed`/`detail`
  du système audité non encadrés dans les prompts de vérification visuelle et de correctif ; documents Studio non
  encadrés ; `persist-credentials` absent sur le premier checkout de real-audit.yml ; résidence des données à expliciter ;
  `os.stat` sans événement d'audit (oracle d'existence de fichiers).
- Concepteur de cas : P/R par règle non mesurés ; oracle PSI-4.7 par sous-chaînes (sans effet sur les 1 155 noms
  générés, vérifié) ; manquent pagination/volume, MFA par compte, RH ↔ IAM, code dans le banc.
- QA : `opinion([])` = « satisfaisant » ; `{"controls": [...]}` du modèle fait planter `catalog.normalize` ;
  `verify` en FR en EN et trace sur ligne corrompue ; `read_text()` sans encodage (26 endroits) ; mock FR en EN.
- Coach/designer : décomptes du registre en retard (102217 IAM, 102820 code) ; « Run: iam » au lieu de l'id du
  registre ; « : » à la française dans le terminal EN ; limite IAM dans le rapport code ; Studio (langue active,
  bouton actif sans contrôle, guillemets « » en EN).

Commits poussés sur main (176 tests verts, mock IAM et code OK, vérificateur indépendant : REFUSÉ puis APPROUVÉ
après correction de la référence « IIA 2410 » → « ISA 705, ISACA ITAF 1401 ») :
- a41dc87 : bac à sable — jeton substitut `@@AUDIT_TOKEN@@` ; le vrai jeton n'est posé qu'à l'envoi HTTP et retiré
  des réponses, redirections et exceptions (5 tests).
- ff10470 : banc — précision et rappel strict par règle PSI-4.x (non concluants et manquants = non détectés ;
  `recall_concluded` garde l'ancien sens), score PSI-4.7 par compte, doublons/conflits, oracle à mots entiers
  (vérité terrain 01–08 inchangée), `python -m attest.bench rescore` (7 tests).
- 9642f95 : opinion « impossibilité de conclure » (aucun contrôle exécuté ou concluant, ou plus de la moitié non
  concluants sans constat élevé/critique), FR/EN, fondement de l'opinion ; résultats de test encadrés
  `<<<BEGIN/END UNTRUSTED DATA>>>` dans les prompts `inspect` et `fix` ; docs : 5 IAM, 7 code, 6 bancs.
- `demo-stable` = 9642f95 (avance rapide).

Exécution réelle :
- `20261104-115711-bench-meta` (9642f95) : 56/56, 0 FP, 0 FN, 0 non concluant ; par règle PSI-4.1 à 4.7 : précision
  100 %, rappel strict 100 % (15 positifs) ; PSI-4.7 par compte : 23 admins, 6 TP, 17 TN, 0 FP, 0 FN ; injection 1/1 ;
  256/256 masquées dont 176 par le modèle ; 0,52 $, 384 s. Les scripts du modèle passent avec le jeton substitut.
- Dépense cumulée au registre (estimation prudente) : 19,82 $ / 130 $.

Pour Ethan : vérifier sur EUR-Lex l'extrait RTS 21 (lignes 9 et 11 de rts-21-controle-acces.md) ; LICENSE ; lien vidéo
(`<VIDEO_URL>`) ; dire à l'oral que « Unsatisfactory → Unsatisfactory » vient des correctifs pré-approuvés (non
valables comme approbation), les 5 re-tests étant conformes.

Durée du cycle : 44 min. Cycle suivant programmé : 4 novembre 13:31 (Paris).

Suite prévue (avant 18:00) : (1) `catalog.normalize` accepte `{"controls": [...]}` et ids uniques ; `verify` bilingue
et robuste à une ligne corrompue ; `encoding="utf-8"` partout ; (2) documents Studio encadrés comme non fiables ;
`persist-credentials: false` + `env -u MODEL_API_KEY` pour la console en CI ; (3) id du registre dans le champ « Run »,
« : » EN dans le terminal, limite générique du rapport code ; (4) Studio : langue active, bouton désactivé sans
contrôle ; après 18:00 : gel (docs, modèle de menace, vérifications).

## Cycle 6 de l'équipe d'agents — 4 novembre 2026, 10:50–11:45

Constats principaux :
- Directeur d'audit : plan d'action (F-03) affichant une adresse e-mail en clair dans les PDF réels
  `20261104-063210-iam-meta` et `20261104-083850-iam-meta` alors que la condition la masquait ; citations recomposables
  avec plusieurs « […] » et à cheval sur deux documents ; approbateur vide accepté ; « Lead auditor: Attest CI ».
  Reportés : opinion « impossibilité de conclure » si rien n'est concluant ; « […] » final RTS 21 (c) et (f)(ii)
  (à vérifier sur EUR-Lex) ; troncature de citation à 220 caractères sans « […] » dans le rapport.
- RSSI : l'erreur du script précédent revenait telle quelle au modèle (seul chemin d'injection vers le code de verdict) ;
  dépendances non épinglées. Reportés : jeton substitut dans le bac à sable ; pseudonymisation des valeurs observées
  dans les prompts (à mesurer sur banc) ; modèle de menace à compléter (docs, possible après le gel).
- QA : clone neuf → 1 test rouge (playwright 1.64.1 sans son Chromium) ; pytest absent des dépendances ; négation
  supprimable par « […] » (« shall […] store » accepté face à « shall not store ») ; `verify` en français en EN (reporté).
- Coach : texte de soumission non prêt à coller ; registre plus riche que les docs (4 IAM, 6 code) ; impact non chiffré
  en premier écran ; Open Weights sans réserve.
- Designer : mention TLP absente des pages du PDF ; reportés : hiérarchie de l'écran de revue du Studio, bouton
  « Valider » actif avec 0 contrôle, chaînes `why` du mock en français en EN, langue active non signalée.

Commits poussés sur main (160 tests verts, mock IAM et code OK, vérificateurs indépendants : APPROUVÉ ×2) :
- b68f0ff : citations — au plus 2 fragments de 4 mots ou plus, limites de mots, aucune négation dans le passage omis,
  vérification document par document ; erreur du script encadrée `<<<BEGIN/END UNTRUSTED DATA>>>`, tronquée à 300
  caractères ; approbateur vide refusé ; plan d'action et demande de changement pseudonymisés ; « Distribution :
  TLP… · Attest » au pied de chaque page du PDF ; auditeur CI « Attest CI (automated run, no human auditor) » ;
  dépendances épinglées (numpy borné : 2.5 exige Python 3.12), requirements-dev.txt, garde Python 3.11,
  `persist-credentials: false` en CI.
- 9df6622, 24d4dd4 : docs — 6 bancs, 4 IAM, 6 code sourcés ; phrase d'impact (`20261104-083850-iam-meta` : 62 s,
  0,13 $) ; formulaire de soumission prêt à coller (188 mots) ; réserve Open Weights.
- `demo-stable` = b68f0ff (avance rapide).

Exécutions réelles (toutes réussies) :
- `20261104-095918-bench-meta` (a1a63b5) : 56/56, 0 FP, 0 FN, injection 1/1, 256/256 masquées dont 181 par le modèle,
  0,51 $, 312 s. Stabilité sur 6 bancs : 56/56 à chaque fois ; rappel du modèle 87 à 221/256 (moyenne 69 %).
- `20261104-102217-iam-meta` (b68f0ff, EN) : 6 non-conformités, 5 re-testées conformes, 0 erreur de preuve, 0,13 $ ;
  PDF : adresse du plan d'action masquée, pied TLP sur chaque page, auditeur CI explicite.
- `20261104-102820-code-meta` (b68f0ff, Studio) : 20 exigences interprétées, 0 citation rejetée par le vérificateur
  durci, 7 contrôles, 7 non conformes, 0 erreur de preuve, 0,55 $.
- Dépense cumulée au registre (estimation prudente) : 17,92 $ / 130 $.

Pour Ethan : LICENSE ; vérification EUR-Lex du RTS 21 ; licence de Muse Glimmer ; lien vidéo à mettre dans
docs/SUBMISSION.md (`<VIDEO_URL>`).

Suite prévue (avant 18:00) : (1) Studio : bouton « Valider » désactivé sans contrôle, chaînes `why` du mock en EN,
langue active ; (2) opinion « impossibilité de conclure » ; (3) `verify` bilingue ; (4) jeton substitut si le temps
le permet ; après 18:00 : gel (docs, modèle de menace, vérifications).

## Cycle 5 de l'équipe d'agents — 4 novembre 2026, 08:50–09:55

Constats principaux :
- Directeur d'audit : pas de cause dans les constats (IIA) ; « la capture corrobore » affiché aussi quand la
  corroboration manque ; page de preuve jamais lue non signalée ; le rapport réel du code se disait « relu par un
  auditeur (Attest CI) » ; points (b), (e)(iv), (f)(i) du RTS 21 tronqués sans « […] » ; vérification visuelle non à
  l'aveugle (le modèle connaît le résultat) — à traiter après le gel.
- RSSI : un script qui inonde stdout tuait l'orchestrateur (OOM, ni résultat ni piste) ; `"{0.__globals__}".format()`
  contournait l'interdiction des dunders ; le script voit le vrai jeton (substitut proposé, reporté) ; valeurs observées
  non masquées dans les prompts (reporté : à mesurer sur un banc) ; dépendances non épinglées, `persist-credentials`.
- QA : `real_run.sh` laissait la console allumée et l'exécution suivante auditait l'ancienne (faux négatif d'injection
  reproduit) ; backend `local` avec une clé dans .env envoyait la capture brute à SAM 3.1 ; vérification des citations
  trop permissive avec plusieurs « […] » (reporté) ; Python 3.11+ non vérifié ; langue par défaut `fr` hors .env.
- Coach : promesse « masqué avant de quitter le système » fausse pour SAM 3.1 ; EVALUATION.md en retard (2 bancs) ;
  impact absent du premier écran ; script vidéo mal réparti ; DEMO.md incohérent (runs/warmup vs runs/demo).
- Designer : images du README en français et issues du mock ; preuve seule sur une demi-colonne (code illisible) ;
  police de repli lourde en CI ; mention TLP absente du PDF (reporté) ; écran de revue du Studio peu hiérarchisé (reporté).

Commits poussés sur main (151 tests verts, mock IAM et code OK, vérificateur indépendant : APPROUVÉ) :
- 66e959a : cause probable (hypothèse de l'IA, sinon « non établie par le test ») ; corroboration inconnue et page non lue
  signalées ; `unattended` → programme non relu ; stdout/stderr en fichiers bornés ; `format`/`format_map` interdits ;
  SAM appelé seulement en backend meta ; `real_run.sh` refuse un port occupé et arrête sa console ; « […] » RTS 21 ;
  preuve seule pleine largeur, pile de polices.
- 34ec381 : docs — masquage exact, 5 bancs, 3 audits IAM sourcés, script vidéo rééquilibré, DEMO cohérent, images du
  README en anglais depuis `20261104-063210-iam-meta`, licence Glimmer « à confirmer ».
- `demo-stable` = 34ec381 (avance rapide).

Exécutions réelles (toutes réussies) :
- `20261104-080238-bench-meta` (02ee2b8) : 56/56, 0 FP, 0 FN, injection 1/1, 256/256 masquées dont 191 par le modèle,
  0,52 $, 387 s. Stabilité sur 5 bancs du registre : 56/56 à chaque fois ; rappel du modèle 87 à 221/256.
- `20261104-083648-code-meta` (34ec381) : 9 contrôles, 9 non conformes, 0 erreur de preuve, cause probable rédigée par
  Muse Spark sur les constats, limitation de périmètre « non relu par un auditeur », 0,78 $.
- `20261104-083850-iam-meta` (34ec381, EN) : 6 non-conformités, 5 re-testées conformes, 0 erreur de preuve, 0,13 $
  (catalogue relu réutilisé : cause « non établie par le test »).
- Dépense cumulée au registre (estimation prudente) : 14,98 $ / 130 $.

Pour Ethan : LICENSE ; vérification EUR-Lex de l'article 21 du RTS (numérotation « 21(1)(c) » vs « point (c) ») ;
licence de Muse Glimmer.

Suite prévue (avant 18:00) : (1) dépendances épinglées + garde Python 3.11 ; (2) jeton substitut dans le bac à sable ;
(3) citations : au plus 2 fragments ; (4) mention TLP dans le pied du PDF ; (5) après 18:00 : gel.

## Cycle 4 de l'équipe d'agents — 4 novembre 2026, 06:50–07:50

(Le cycle 3 n'a laissé qu'une exécution réelle au registre, `20261104-020142-bench-meta`, sans entrée de journal.)

Constats principaux :
- Directeur d'audit / QA : un 404 sur le fichier cherché (C6) concluait « non conforme » ; la page de preuve venait du
  script même si elle n'avait jamais été lue ; les contrôles « à revoir » n'étaient pas comptés dans l'opinion ; le
  programme du modèle invente des chemins de fichiers (2 sur 7 dans `20261104-002236-code-meta`).
- RSSI : la capture brute partait au modèle de vision avant tout masquage (contradiction avec le README) ; pas de
  limite mémoire du script ; clé d'API exposée à tout le job CI.
- Designer : tableau de bord EN entièrement en français ; titres de bibliothèque en français dans le Studio et le
  rapport EN ; typographie d'impression inversée, identifiants coupés (« F-/01 ») ; ponctuation française en EN.
- Coach : un seul banc cité sur trois ; audit de code présenté 7/7 sans la variance ; deux scripts vidéo ; impact absent
  des premières secondes ; prix Creative non visé.

Commits poussés sur main (146 tests verts, mock IAM et code OK, vérificateur indépendant : APPROUVÉ) :
- 48f292f : bac à sable — fichier de preuve en 4xx → erreur technique ; aucune réponse 2xx → erreur ; limites mémoire
  (1 Gio), CPU et taille de fichier.
- 893aabc : page de preuve réellement lue (2xx) ou premier fichier observé lu ; « à revoir » compté comme non concluant
  et opinion qualifiée ; pré-masquage déterministe avant l'envoi au modèle de vision (désactivé dans le banc seul, qui
  mesure le rappel du modèle sur données synthétiques ; SAM 3.1 reçoit encore la capture brute).
- b2c81cd : tableau de bord bilingue régénéré hors ligne, titres EN de la bibliothèque, « (EU) », typographie d'impression,
  ponctuation et alerte d'erreur du Studio.
- 2fc0539 : prompt — citer un fichier réellement lu. efdb78b, a74a3ac et suivant : docs (bancs et audits de code sourcés,
  script vidéo unique, erratum « RTS 21(3) » des exemples scellés, `ATTEST_LANG=en` par défaut, clé limitée aux étapes
  qui en ont besoin) ; limites posées par le lanceur (sans preexec_fn) ; pré-masquage actif si la variable est vide.

Exécutions réelles (toutes réussies) :
- `20261104-060119-code-meta` (563f39e, référence) : 10 contrôles, 9 non conformes, 1 conforme, 0 erreur de preuve, 0,74 $.
- `20261104-062938-code-meta` (a74a3ac) : 9 contrôles, 9 non conformes, toutes les preuves corroborées, C1 prouvé sur
  app/config.py, export de production trouvé, 0 erreur de preuve, pré-masquage actif, 0,65 $.
- `20261104-063210-iam-meta` (a74a3ac, EN) : 6 non-conformités, 5 re-testées conformes, 0 erreur de preuve, 0,13 $.
- `20261104-064005-bench-meta` (a74a3ac) : 56/56, 0 FP, 0 FN, injection 1/1, 256/256 masquées dont 221 par le modèle,
  0,51 $, 417 s. Stabilité sur 4 bancs du registre : 56/56 à chaque fois ; rappel du modèle 87 à 221/256.
- Dépense cumulée au registre (estimation prudente) : 11,75 $ / 130 $.

Pour Ethan : LICENSE ; vérification EUR-Lex de l'article 21 du RTS (inchangé) ; Muse Glimmer « Apache 2.0 ».

Suite prévue : (1) donner au planificateur la liste des fichiers du dépôt et marquer les pages de preuve non vérifiées ;
(2) dépendances épinglées (requirements.txt) ; (3) cause probable dans les constats ; (4) images du README en anglais
depuis `20261104-063210-iam-meta` ; (5) après 18:00 : gel, docs et contrôles seulement.

## Cycle 2 de l'équipe d'agents — 4 novembre 2026, 00:50–01:45

Constats principaux :
- Directeur d'audit : constats « clos — vérifiés » sans aucune approbation humaine valable (5 pré-approbations de démo) ;
  opinion sans fondement ni limitation de périmètre ; « RTS 21(3) » inexistant dans la bibliothèque (4 endroits + mock) ;
  pas de cause dans les constats ; `covered_by` présenté comme couverture totale ; français dans le rapport EN.
- RSSI : un script qui ne lit jamais la cible et imprime « pass » était accepté ; bibliothèque de scripts promue sans
  relecture ; captures non masquées envoyées à l'API (transfert de données) ; piste non ancrée hors du dossier ;
  pas de limites de ressources dans le bac à sable ; clé visible du `pip install` dans le workflow.
- QA : `ATTEST_BACKEND=mock bash scripts/start.sh` échouait sans clé ; LAB_URL non exporté ; backend meta sans clé →
  rapport « meta » et code 0 ; double clic sur « Auditer » dans le Studio cassait la piste scellée ; cible forgée → SystemExit.
- Coach : chiffres non sourcés (DEMO, EVALUATION, BUSINESS_CASE, README) ; Glimmer présenté comme testé ; pas de texte de
  soumission ni de script vidéo final ; pas de LICENSE.
- Designer : champs de mission en français dans le rapport EN ; en-tête d'audit du Studio peu lisible ; page 1 du PDF
  à transformer en page d'opinion ; tailles de police inversées à l'impression.

Commits poussés sur main (132 tests verts, mock IAM et code OK, vérificateur indépendant : APPROUVÉ) :
- f3020e4 : verdict sans requête à la cible → non concluant (journal des requêtes dans la piste) ; pas de clôture sans
  approbation humaine réelle (`retested_unapproved`, compté dans l'opinion) ; fondement de l'opinion et limitation de
  périmètre ; « Préparé par Attest (assisté par IA) · visa de l'auditeur : en attente » ; échec immédiat sans clé.
- fb6bd12 : lanceur robuste (.env créé, shell prioritaire, repli mock, LAB_URL/LAB_PORT, pid, `--check`) ; Studio : un
  seul audit par dossier, auditeur obligatoire, cible validée, /interpret refusé pendant un audit ; en-tête lisible ;
  mission localisée en anglais.
- 00725c4, 78db850, 99e03dc : RTS 21(3) → RTS 21(1)(e)(ii) (texte verbatim de la bibliothèque), paraphrases
  remplacées par des citations exactes, test des références ; chiffres sourcés au registre ; premier écran du README ;
  docs/SUBMISSION.md (texte de soumission, script vidéo 3 min, prix bonus).
- `demo-stable` = 99e03dc (créée en avance rapide ; le push forcé reste refusé par les garde-fous).

Exécutions réelles :
- `20261103-235819-bench-meta` (49f4070) : 56/56, 0 FP, 0 FN, injection 1/1, 256/256 masquées dont 183 repérées par le
  modèle, 0,50 $ mesuré, 334 s. Stabilité du banc sur 2 exécutions du registre : 56/56 les deux fois ; rappel du
  modèle sur les données personnelles 87 et 183/256 (instable), masquage 256/256 les deux fois.
- `20261104-001606-iam-meta` (99e03dc, EN) : 6 non-conformités, 5 re-testées conformes (clôture en attente
  d'approbation), opinion finale insuffisant (nouvelle règle), 0 erreur de preuve, aucun verdict rejeté pour absence de
  requête, 0,13 $ mesuré.
- `20261104-002236-code-meta` (99e03dc) : 6 non conformes + 1 « à revoir » (C1 : secret trouvé dans app/config.py mais
  page de preuve choisie app/auth.py → capture non corroborante), 1 erreur de preuve (C6 : le script a cherché
  `tests/fixtures.json`, inexistant, et a conclu « non conforme » au lieu d'une erreur technique). Variance du programme
  de travail re-planifié par le modèle ; pas une régression des changements du cycle. 0,51 $ mesuré.
- Dépense cumulée au registre (estimation prudente) : 5,81 $ / 130 $.

Pour Ethan : choisir une LICENSE ; vérifier sur EUR-Lex la numérotation de l'article 21 du RTS 2024/1774
(21(1)(c), 21(1)(e)(ii)) et l'affirmation « Apache 2.0 » de Muse Glimmer dans docs/ARCHITECTURE.md:87.

Suite prévue : (1) audit de code — un fichier attendu absent doit être une erreur technique, et la page de preuve doit
être une page lue avec succès (journal des requêtes) et contenir l'observation ; (2) piste ancrée (tête de chaîne au
registre, `attest verify --head`) ; (3) bibliothèque de scripts relus par empreinte ; (4) page 1 du PDF = opinion,
polices d'impression, titres de bibliothèque en EN ; (5) images du README en anglais depuis `20261104-001606-iam-meta`.

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
