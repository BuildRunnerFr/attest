# Politique interne PSI-5 (Banque Kerlann, fictive) — cycle de vie des accès
Déclinaison interne de DORA 9(4)(c) et du RTS 2024/1774 article 21 : elle fixe les délais que les textes ne donnent pas.


Les comptes sont rapprochés du registre RH à une date de situation (`as_of`) ; seuls les comptes actifs donnent
un accès et entrent dans le champ des règles. La criticité de chaque règle est fixée par le propriétaire de la
politique (RSSI) et s'applique aux constats.

| Règle | Exigence | Criticité | Fondement |
|---|---|---|---|
| PSI-5.1 | Départ : le compte d'un salarié est désactivé au plus tard le jour de la fin de son contrat. Un compte de personne encore actif alors que la date de fin de contrat de son titulaire est antérieure à la date de situation est non conforme (une fin de contrat le jour même ou à venir ne l'est pas). | Critique | DORA 9(4)(c) ; RTS 21(1)(e) |
| PSI-5.2 | Rattachement : tout compte actif est rattaché à un responsable connu. Un compte de personne actif dont le matricule est absent du registre RH, ou un compte de service actif dont le responsable est absent du registre ou a quitté l'entreprise, est non conforme. Le compte d'une personne présente au registre mais partie relève de PSI-5.1 seulement, pas de cette règle. | Élevée | DORA 9(4)(c) ; RTS 21(1)(e) |
| PSI-5.3 | Comptes dormants : un compte de personne actif sans connexion depuis plus de 90 jours (à défaut de connexion, depuis sa création) est non conforme ; 90 jours exactement restent conformes. Les comptes de service ne sont pas concernés. | Moyenne | DORA 9(4)(c) ; RTS 21(1)(a) |
| PSI-5.4 | Séparation des tâches : aucun compte actif ne cumule `paiements.saisie` et `paiements.validation`, ni `credit.instruction` et `credit.decision`. | Critique | RTS 21(1)(b) |
| PSI-5.5 | Mutation : au plus tard 30 jours après un changement de service, les droits rattachés à l'ancien service sont retirés. Un compte actif qui détient encore un droit de l'ancien service de son titulaire plus de 30 jours après la date de mutation est non conforme ; 30 jours exactement restent conformes. Les droits communs (sans service) ne sont pas concernés. | Élevée | RTS 21(1)(a) ; RTS 21(1)(e) |
| PSI-5.6 | Revue des accès à privilèges : tout compte actif détenant un droit à privilèges a fait l'objet d'une revue d'accès depuis 365 jours au plus ; une revue absente ou plus ancienne est non conforme. | Moyenne | RTS 21(1)(e)(iv) |

## Délais de remédiation (politique interne)
Critique : 30 jours · Élevée : 90 jours · Moyenne : 180 jours · Faible : 365 jours, à compter de la date du rapport.
Toute correction suit le processus de gestion des changements (ticket, approbation, journalisation, vérification).
