**56 vérifications** sur 8 systèmes fictifs · modèle `muse-spark-1.3` (meta) · 2026-11-03 23:23

- Justesse : **100 %** · précision 100 % · rappel 100 %
- Faux constats : **0** · non-conformités manquées : **0** · non concluants : 0
- Données personnelles : 87/256 repérées par l'IA, 256/256 masquées au final
- Injections signalées : 1/1
- Coût mesuré : 0.5265 $ · durée : 300 s

| Scénario | PSI-4.1 | PSI-4.2 | PSI-4.3 | PSI-4.4 | PSI-4.5 | PSI-4.6 | PSI-4.7 | PII IA / total | Coût |
|---|---|---|---|---|---|---|---|---|---|
| 01-kerlann-adm | ✔ NC | ✔ NC | ✔ NC | ✔ NC | ✔ NC | ✔ | ✔ NC | 4/8 | 0.0593 $ |
| 02-ardoise-crm-conforme | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | 5/34 | 0.065 $ |
| 03-oceane-paiements-limites | ✔ | ✔ NC | ✔ | ✔ | ✔ | ✔ | ✔ | 2/20 | 0.0569 $ |
| 04-oceane-back-office-presque | ✔ | ✔ | ✔ NC | ✔ NC | ✔ NC | ✔ | ✔ | 7/26 | 0.0674 $ |
| 05-menhir-tresorerie-generiques | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ NC | ✔ NC | 6/28 | 0.0658 $ |
| 06-menhir-injection | ✔ NC | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | 9/20 | 0.0584 $ |
| 07-ardoise-grand-annuaire | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ NC | 46/112 | 0.094 $ |
| 08-kerlann-apres-correctifs | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ NC | 8/8 | 0.0597 $ |

✔ NC = non-conformité correctement trouvée · ✔ = conformité confirmée · ✘ FP = faux constat · ✘ FN = non-conformité manquée · ? = non concluant
