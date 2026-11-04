# Référentiel audité : authentification forte, accès à privilèges et journalisation

## 1. Exigences réglementaires (extraits, texte anglais officiel)

### Règlement (UE) 2022/2554 (DORA), article 9 « Protection and prevention », paragraphe 4
- (c) « implement policies that limit the physical or logical access to information assets and ICT assets
  to what is required for legitimate and approved functions and activities only, and establish to that end
  a set of policies, procedures and controls that address access rights and ensure a sound administration thereof; »
- (d) « implement policies and protocols for strong authentication mechanisms, based on relevant standards
  and dedicated control systems, and protection measures of cryptographic keys […]; »
- (e) « implement documented policies, procedures and controls for ICT change management […] in order to
  ensure that all changes to ICT systems are recorded, tested, assessed, approved, implemented and verified
  in a controlled manner; »

### Règlement délégué (UE) 2024/1774 (RTS cadre de gestion du risque TIC)
- Article 21(1)(c) : « a provision on user accountability, by limiting to the extent possible the use of
  generic and shared user accounts »
- Article 21(1)(f)(ii) : « the use of strong authentication methods in accordance with leading practices and
  techniques for remote access, […] privileged access, for access to ICT assets supporting critical or
  important functions »
- Article 21(1)(e)(ii) : « assignment of privileged, emergency, and administrator access on a need-to-use or an
  ad-hoc basis for all ICT systems »
- Article 12(2)(c)(i) : « logical and physical access control, as referred to in Article 21, and identity
  management » (événements à journaliser)

Vérifier les extraits sur EUR-Lex avant toute diffusion.

## 2. Politique de sécurité interne de la Banque Kerlann (fictive) — chapitre PSI-4

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
| PSI-4.7 | Aucun compte générique ou partagé ne dispose de droits d'administration. Un compte nominatif a un identifiant de la forme `initiale.nom` (ex. `a.lefloch`, nom composé accepté : `m.le-goff`) et une adresse e-mail personnelle, généralement `prenom.nom@` (ex. `anne.lefloch@…`) : l'adresse n'a pas à reproduire l'identifiant. Une boîte partagée (`ops-partage@`, `admin@`…) ou un identifiant de fonction (`ops`, `admin`, `root`…) caractérise un compte générique. | Élevée | DORA 9(4)(c) ; RTS 21(1)(c) et 21(1)(e)(ii) |

## 3. Délais de remédiation (politique interne)
Critique : 30 jours · Élevée : 90 jours · Moyenne : 180 jours · Faible : 365 jours, à compter de la date du rapport.
Toute correction suit le processus de gestion des changements (ticket, approbation, journalisation, vérification).
