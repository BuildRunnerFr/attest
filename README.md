# Attest — l'agent d'audit qui teste au lieu de lire

Projet pour le **Meta Global AI Developer Hackathon** (track « Build for Your World »).

On donne à Attest une exigence réglementaire (ici DORA, article 9, authentification forte) et la
politique interne qui la décline. L'agent :

1. **planifie** les contrôles techniques (Muse Spark) ;
2. **écrit le script de chaque contrôle** et l'exécute dans un bac à sable en lecture seule (Muse Spark) ;
3. **capture la preuve** (capture d'écran de la console) et vérifie qu'elle corrobore le résultat (Muse Spark, vision) ;
4. **surligne** la ligne qui fait foi et **floute les données personnelles** de la preuve (SAM 3.1) ;
5. **corrige** la non-conformité, **rejoue** le même script et capture la preuve « après » ;
6. produit un **rapport d'audit** HTML, qui se met à jour en direct pendant l'exécution.

L'environnement audité est une console d'administration d'une banque **fictive** (`lab/`).
Aucune donnée réelle.

## Démarrage

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 1. la console fictive (terminal 1)
python -m lab.app                       # http://127.0.0.1:5050/admin/security

# 2. l'agent (terminal 2)
cp .env.example .env                    # puis renseigner MODEL_API_KEY
set -a; source .env; set +a
python -m attest exigences/dora_authentification.md
# ouvrir runs/<date>/report.html (il se recharge seul pendant l'audit)
```

Sans clé : `ATTEST_BACKEND=mock` fait tourner tout le pipeline avec des réponses préenregistrées.

## Backends (`ATTEST_BACKEND`)

| Valeur | Modèles | Usage |
|---|---|---|
| `meta` | Muse Spark 1.3 + SAM 3.1 via `https://api.meta.ai/v1` | démo principale |
| `local` | Muse Glimmer servi par toi (llama.cpp `llama-server`, vLLM, SGLang), SAM via l'API | prix Open Weights : les preuves d'audit ne sortent pas |
| `mock` | réponses préenregistrées | développement sans clé |

## Garde-fous (la partie « sécurité » du projet)

- Les scripts écrits par le modèle sont analysés **avant exécution** (AST) : imports en liste blanche,
  aucune requête HTTP en écriture, pas d'`exec`/`eval`/`open`. Un contrôle est forcément en lecture seule.
- Les correctifs proposés passent par une liste blanche (une route, des clés connues).
- La capture brute non floutée est supprimée ; seule la preuve floutée est conservée.
- La précision du floutage est **mesurée** contre le DOM de la page (vérité terrain jamais montrée au modèle).

## Structure

```
lab/            console fictive (Flask) + API.md donnée à l'agent
exigences/      exigences et politique interne (fictive)
attest/
  pipeline.py   la boucle de l'agent
  llm.py        accès aux modèles (meta / local / mock)
  sam.py        appel SAM 3.1 + décodage des masques (meta-sam-parser)
  sandbox.py    garde-fou statique + exécution des scripts
  evidence.py   captures Playwright + vérité terrain DOM
  report.py     rapport HTML
  mock.py       réponses préenregistrées
```

## Points à vérifier avec la vraie API

- `input_image` avec une URL `data:` (base64) : si SAM ou Muse Spark la refusent, définir
  `PUBLIC_EVIDENCE_BASE_URL` et servir le dossier `runs/` en HTTPS (VPS ou tunnel).
- La qualité des boîtes renvoyées par Muse Spark sur une capture d'écran : SAM les affine, et en
  cas d'échec de SAM le pipeline se rabat sur la boîte.
- Le texte de DORA cité dans `exigences/` est un résumé : le vérifier sur EUR-Lex.
