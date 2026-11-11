# Référentiel audité : cycle de vie des accès (départs, mutations, séparation des tâches, revues)

## 1. Exigences réglementaires (extraits, texte anglais officiel)

### Règlement (UE) 2022/2554 (DORA), article 9 « Protection and prevention », paragraphe 4
- (c) « implement policies that limit the physical or logical access to information assets and ICT assets
  to what is required for legitimate and approved functions and activities only, and establish to that end
  a set of policies, procedures and controls that address access rights and ensure a sound administration thereof; »

### Règlement délégué (UE) 2024/1774 (RTS cadre de gestion du risque TIC)
- Article 21(1)(a) : « the assignment of access rights to ICT assets based on need-to-know, need-to-use and
  least privilege principles »
- Article 21(1)(b) : « the segregation of duties designed to prevent unjustified access to critical data […] »
- Article 21(1)(e) : « account management procedures to grant, change or revoke access rights for user and
  generic accounts »
- Article 21(1)(e)(iv) : « update of access rights where changes are necessary and at least once a year for all
  ICT systems […] »

Vérifier les extraits sur EUR-Lex avant toute diffusion.

## 2. Politique de sécurité interne de la Banque Kerlann (fictive) — chapitre PSI-5

Les comptes sont rapprochés du registre RH à une date de situation (`as_of`) ; seuls les comptes actifs donnent
un accès et entrent dans le champ des règles. La criticité de chaque règle est fixée par le propriétaire de la
politique (RSSI) et s'applique aux constats.

| Règle | Exigence | Criticité | Fondement |
|---|---|---|---|
| PSI-5.1 | Départ : le compte d'un salarié est désactivé au plus tard le jour de la fin de son contrat. Un compte de personne encore actif alors que la date de fin de contrat de son titulaire est antérieure à la date de situation est non conforme (une fin de contrat le jour même ou à venir ne l'est pas). | Critique | DORA 9(4)(c) ; RTS 21(1)(e) |
| PSI-5.2 | Rattachement : tout compte actif est rattaché à un responsable connu. Un compte de personne actif dont le matricule est absent du registre RH, ou un compte de service actif dont le responsable est absent du registre ou a quitté l'entreprise, est non conforme. | Élevée | DORA 9(4)(c) ; RTS 21(1)(e) |
| PSI-5.3 | Comptes dormants : un compte de personne actif sans connexion depuis plus de 90 jours (à défaut de connexion, depuis sa création) est non conforme ; 90 jours exactement restent conformes. Les comptes de service ne sont pas concernés. | Moyenne | DORA 9(4)(c) ; RTS 21(1)(a) |
| PSI-5.4 | Séparation des tâches : aucun compte actif ne cumule `paiements.saisie` et `paiements.validation`, ni `credit.instruction` et `credit.decision`. | Critique | RTS 21(1)(b) |
| PSI-5.5 | Mutation : au plus tard 30 jours après un changement de service, les droits rattachés à l'ancien service sont retirés. Un compte actif qui détient encore un droit de l'ancien service de son titulaire plus de 30 jours après la date de mutation est non conforme ; 30 jours exactement restent conformes. Les droits communs (sans service) ne sont pas concernés. | Élevée | RTS 21(1)(a) ; RTS 21(1)(e) |
| PSI-5.6 | Revue des accès à privilèges : tout compte actif détenant un droit à privilèges a fait l'objet d'une revue d'accès depuis 365 jours au plus ; une revue absente ou plus ancienne est non conforme. | Moyenne | RTS 21(1)(e)(iv) |

## 3. Délais de remédiation (politique interne)
Critique : 30 jours · Élevée : 90 jours · Moyenne : 180 jours · Faible : 365 jours, à compter de la date du rapport.
Toute correction suit le processus de gestion des changements (ticket, approbation, journalisation, vérification).
