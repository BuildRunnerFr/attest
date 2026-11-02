# Politique interne PSI-4 (Banque Kerlann, fictive) — authentification et accès
Déclinaison interne de DORA 9(4)(c)(d) et du RTS 2024/1774 articles 12 et 21 : elle fixe les seuils que les textes ne donnent pas.


Le système KRL-ADM supporte des fonctions critiques ou importantes. La criticité de chaque règle est fixée
par le propriétaire de la politique (RSSI) et s'applique aux constats.

| Règle | Exigence | Criticité | Fondement |
|---|---|---|---|
| PSI-4.1 | Authentification multifacteur obligatoire pour tout compte à privilèges (administrateur). | Critique | DORA 9(4)(d) ; RTS 21(1)(f)(ii) |
| PSI-4.2 | Authentification multifacteur obligatoire pour les utilisateurs d'un système supportant une fonction critique ou importante. | Élevée | DORA 9(4)(d) ; RTS 21(1)(f)(ii) |
| PSI-4.3 | Mot de passe de 12 caractères minimum, avec exigence de complexité. | Moyenne | DORA 9(4)(d) (bonnes pratiques) |
| PSI-4.4 | Verrouillage du compte après 5 échecs de connexion au plus (et jamais désactivé). | Moyenne | DORA 9(4)(c) |
| PSI-4.5 | Expiration des sessions inactives après 15 minutes au plus (et jamais désactivée). | Moyenne | DORA 9(4)(c) |
| PSI-4.6 | Journalisation de toutes les actions d'administration. | Élevée | RTS 12(2)(c)(i) |
| PSI-4.7 | Aucun compte générique ou partagé ne dispose de droits d'administration. Un compte nominatif a un identifiant de la forme `initiale.nom` (ex. `a.lefloch`, nom composé accepté : `m.le-goff`) et une adresse e-mail personnelle, généralement `prenom.nom@` (ex. `anne.lefloch@…`) : l'adresse n'a pas à reproduire l'identifiant. Une boîte partagée (`ops-partage@`, `admin@`…) ou un identifiant de fonction (`ops`, `admin`, `root`…) caractérise un compte générique. | Élevée | DORA 9(4)(c) ; RTS 21(1)(c) et 21(3) |

## Délais de remédiation (politique interne)
Critique : 30 jours · Élevée : 90 jours · Moyenne : 180 jours · Faible : 365 jours, à compter de la date du rapport.
Toute correction suit le processus de gestion des changements (ticket, approbation, journalisation, vérification).
