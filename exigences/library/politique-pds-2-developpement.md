# Politique interne PDS-2 (Banque Kerlann, fictive) — développement sécurisé
Déclinaison interne de DORA 9(3), du RTS 2024/1774 articles 6, 7, 12 et 16 pour le code applicatif. Elle fixe les règles
précises que les textes réglementaires ne donnent pas.

| Règle | Exigence | Criticité | Fondement |
|---|---|---|---|
| PDS-2.1 | Aucun secret (mot de passe, clé, jeton) n'est écrit en clair dans le code source ni dans la configuration versionnée : les secrets viennent d'un coffre ou de variables d'environnement. | Critique | RTS 7(2) |
| PDS-2.2 | Tout appel réseau sortant vérifie le certificat TLS du serveur : la vérification n'est jamais désactivée (`verify=False` interdit). | Élevée | DORA 9(3)(a) ; RTS 6(2)(a) |
| PDS-2.3 | Les mots de passe sont hachés avec argon2, bcrypt, scrypt ou PBKDF2. MD5 et SHA-1 sont interdits pour tout usage de sécurité. | Élevée | RTS 6(3) et 6(4) |
| PDS-2.4 | La chaîne d'intégration continue exécute une analyse statique de sécurité (bandit, semgrep ou CodeQL) à chaque modification. | Moyenne | RTS 16(3) |
| PDS-2.5 | Les dépendances sont épinglées à une version exacte (`paquet==version`) et auditées en intégration continue (pip-audit ou équivalent). | Moyenne | RTS 16(4) et 16(8) |
| PDS-2.6 | Les données de test sont synthétiques et déclarées comme telles (champ `"synthetic": true`) ; aucun export de production n'est versionné. | Élevée | RTS 16(5)(a) |
| PDS-2.7 | Les réussites et les échecs d'authentification sont journalisés par l'application. | Moyenne | RTS 12(2)(c)(i) |

## Délais de remédiation
Critique : 30 jours · Élevée : 90 jours · Moyenne : 180 jours · Faible : 365 jours.
