# Exemples d'audits réels

## `evaluation-en/` — évaluation sur 8 systèmes fictifs (2 novembre 2026)

Muse Spark 1.3 + SAM 3.1, en anglais, en lecture seule. Ouvrir `evaluation-en/scorecard.html` : chaque scénario renvoie
vers son rapport complet.

- **56/56 vérifications justes** : aucun faux constat, aucune non-conformité manquée, aucun résultat non concluant.
- Injection de prompt signalée (1/1), sans effet sur le verdict.
- Données personnelles : 178/256 repérées par le modèle seul, 256/256 masquées grâce au filet déterministe.
- Coût : 0,65 $ pour les 8 systèmes ; 240 s.

> **Erratum (4 Nov 2026).** These sealed reports predate commit 00725c4 and cite "RTS 21(3)", which does not exist in
> the verified library: read **RTS 2024/1774 art. 21(1)(e)(ii)**. The files are left unchanged so that `attest verify`
> still passes on them; later benchmark runs (ledger `20261104-020142-bench-meta`) use the corrected reference.

Relecture du programme de travail et des scripts écrits pendant cette évaluation (`controls/AUD-2026-IAM-01.en.json`,
`library/PSI-4.*`) :
- Programme fidèle à la politique : 7 règles, criticités, références et type de remédiation corrects.
- Les deux défauts relevés lors du premier audit ont disparu : toute erreur technique sort en code 2 (« test en échec »),
  et l'e-mail n'a plus à reproduire l'identifiant.
- Réserve sur PSI-4.7 : la liste de mots génériques ne contient pas `ops`, `svc` ni `it` (rattrapés ici par la convention
  d'identifiant), et des noms de famille comme `bureau` y figurent : risque de faux positif sur un vrai nom. À corriger
  avant de marquer le programme `"reviewed": true`.

Les scripts du premier audit (français) ont été retirés de la bibliothèque : ils correspondaient à l'ancienne rédaction
de PSI-4.7 et contenaient les deux défauts ci-dessous.

## Premier audit avec les vrais modèles (2 novembre 2026)

Meta Model API : Muse Spark 1.3 + SAM 3.1, 7 contrôles, programme de travail et scripts en cache,
remédiation avec approbation interactive. Le rapport complet a été retiré du dépôt (il contenait un chemin de
fichier local) ; il est remplacé par les rapports de l'évaluation sur 8 systèmes fictifs.

- 6 non-conformités, 5 corrigées sur approbation puis revérifiées, 1 plan d'action (compte partagé « ops »).
- Coût mesuré : 0,135 $ (18 appels Muse Spark, 22 663 jetons en entrée, 25 181 en sortie) ; 12 images SAM.

Ce que cet audit a révélé sur l'outil lui-même, et qui a été corrigé ensuite :
1. Muse Spark a repéré les 8 données personnelles de la page des comptes, mais ses boîtes d'adresses IP
   commençaient environ 40 px trop à droite : le préfixe « 10.12. » restait lisible (4/8 masquées).
   → Ajout d'un filet de sécurité déterministe sur le texte de la page ; le rapport affiche désormais
   ce que l'IA a repéré seule et ce qui est masqué au final.
2. Le champ « Constaté » du contrôle C7 affichait les e-mails en clair.
   → Pseudonymisation des e-mails, IP et IBAN dans le texte du rapport.


## Relecture des scripts et du programme de travail écrits par Muse Spark

Le programme de travail est fidèle à la politique : criticités, références et type de remédiation sont corrects
pour les 7 règles. Deux défauts ont été relevés dans les scripts :

1. **Faux positif sur PSI-4.7** : le script exigeait que la partie locale de l'e-mail soit identique à l'identifiant
   (`anne.lefloch@` ≠ `a.lefloch`). Le compte nominatif `a.lefloch` a donc été compté à tort : 2 non-conformités au lieu
   d'une (seul `ops` est générique). Cause : règle ambiguë. → La règle PSI-4.7 a été clarifiée dans le référentiel.
2. **Erreur technique transformée en non-conformité** : 6 scripts sur 7 concluaient « non conforme » si l'API ne
   répondait pas, ce qui aurait produit de faux constats. → Consigne durcie (code de sortie 2) et garde-fou : pas de
   constat sans valeur constatée ; un tel résultat devient « test en échec ».

Ces corrections invalident le programme de travail et les scripts de cette version : le prochain audit les régénère,
et ils devront être relus à nouveau avant d'être marqués `"reviewed": true`.
