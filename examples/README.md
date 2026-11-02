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
