# Exemples d'audits réels

## `rapport-reel-fr/` — premier audit avec les vrais modèles (2 novembre 2026)

Meta Model API : Muse Spark 1.3 + SAM 3.1, 7 contrôles, programme de travail et scripts en cache,
remédiation avec approbation interactive. Ouvrir `report.html` ou `report.pdf`.

- 6 non-conformités, 5 corrigées sur approbation puis revérifiées, 1 plan d'action (compte partagé « ops »).
- Coût mesuré : 0,135 $ (18 appels Muse Spark, 22 663 jetons en entrée, 25 181 en sortie) ; 12 images SAM.
- Intégrité : `python -m attest verify examples/rapport-reel-fr`.

Ce que cet audit a révélé sur l'outil lui-même, et qui a été corrigé ensuite :
1. Muse Spark a repéré les 8 données personnelles de la page des comptes, mais ses boîtes d'adresses IP
   commençaient environ 40 px trop à droite : le préfixe « 10.12. » restait lisible (4/8 masquées).
   → Ajout d'un filet de sécurité déterministe sur le texte de la page ; le rapport affiche désormais
   ce que l'IA a repéré seule et ce qui est masqué au final.
2. Le champ « Constaté » du contrôle C7 affichait les e-mails en clair.
   → Pseudonymisation des e-mails, IP et IBAN dans le texte du rapport.

Le rapport scellé est conservé tel quel : le modifier casserait sa vérification d'intégrité.

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
