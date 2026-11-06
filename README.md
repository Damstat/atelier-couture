# API de gestion d'un atelier de couture

API REST (FastAPI + PostgreSQL) pour gérer un atelier de couture : clients et historique de leurs
mesures, commandes et suivi de la production, acomptes et soldes, livraisons, statistiques du patron.

- Documentation interactive (Swagger) : http://localhost:8000/docs
- Toutes les routes sont préfixées par `/api/v1`, sauf `/health`.

## Sommaire

1. [Stack technique](#stack-technique)
2. [Démarrage rapide avec Docker](#démarrage-rapide-avec-docker)
3. [Installation locale (développement)](#installation-locale-développement)
4. [Comptes de test](#comptes-de-test)
5. [Lancer les tests](#lancer-les-tests)
6. [Architecture](#architecture)
7. [Routes réalisées](#routes-réalisées)
8. [Règles de gestion](#règles-de-gestion)
9. [Conventions de l'API](#conventions-de-lapi)

## Stack technique

| Élément | Choix |
|---|---|
| Langage | Python 3.12 |
| Framework | FastAPI 0.115 (Swagger sur `/docs`) |
| Base de données | PostgreSQL 16 |
| Accès aux données | SQLAlchemy 2 (`Mapped`, `mapped_column`, `select`) |
| Migrations | Alembic (le schéma se crée uniquement avec `alembic upgrade head`) |
| Validation | Pydantic v2 (schémas Create / Update / Read séparés) |
| Sécurité | JWT signé avec expiration (PyJWT), mots de passe hachés avec Argon2 |
| Tests | pytest + TestClient |
| Conteneurs | Dockerfile + docker-compose (API + PostgreSQL) |

Les versions exactes sont dans [requirements.txt](requirements.txt).

## Démarrage rapide avec Docker

Prérequis : Docker Desktop (ou Docker Engine + Compose v2) et Git.

```bash
git clone https://github.com/Damstat/atelier-couture.git
cd atelier-couture
```

**1. Créer le fichier `.env`** à partir du modèle, puis remplir les valeurs marquées `a-remplacer` :

```bash
cp .env.example .env              # Linux / macOS / Git Bash
Copy-Item .env.example .env       # Windows PowerShell
```

| Variable | Rôle |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Identifiants de la base (créée automatiquement par le conteneur) |
| `POSTGRES_HOST` | `db` dans Docker ; `localhost` pour lancer l'API sur la machine. Dans Docker Compose, l'API force `db`. |
| `SECRET_KEY` | Clé de signature des jetons JWT. Générer : `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de validité d'un jeton (60 par défaut) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NOM` | Premier administrateur créé par le script d'initialisation (mot de passe : 8 caractères minimum) |

Le fichier `.env` est ignoré par Git et par Docker (`.dockerignore`) : aucun secret n'est versionné.

**2. Démarrer :**

```bash
docker compose up --build
```

Au démarrage, le conteneur `api` exécute dans l'ordre :

1. `alembic upgrade head` : crée ou met à jour le schéma ;
2. `python -m app.seed` : crée le premier administrateur et le catalogue de l'annexe B. Le script ne crée que ce qui manque, on peut donc le relancer ;
3. `uvicorn` : l'API écoute sur le port 8000.

**3. Vérifier :**

```bash
curl http://localhost:8000/health        # {"status":"ok"} si la base répond
```

Puis ouvrir http://localhost:8000/docs, cliquer sur **Authorize** et se connecter avec l'e-mail
et le mot de passe de l'administrateur (`ADMIN_EMAIL` / `ADMIN_PASSWORD`).

Arrêter : `docker compose down` (ajouter `-v` pour effacer aussi les données).

## Installation locale (développement)

Pour lancer l'API et les tests directement sur la machine, avec seulement PostgreSQL dans Docker.

```powershell
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dans `.env`, mettre `POSTGRES_HOST=localhost`, puis :

```bash
docker compose up db -d          # PostgreSQL seul, exposé sur le port 5432
alembic upgrade head             # schéma
python -m app.seed               # administrateur + catalogue
uvicorn app.main:app --reload    # http://localhost:8000/docs
```

Pour faire évoluer le schéma : modifier les modèles dans `app/models`, puis
`alembic revision --autogenerate -m "description"` et `alembic upgrade head`.

## Comptes de test

| Compte | Comment l'obtenir |
|---|---|
| Administrateur | Créé par `python -m app.seed` avec `ADMIN_EMAIL` / `ADMIN_PASSWORD` du `.env` (par défaut `admin@atelier.sn`) |
| Accueil, tailleur | Créés par l'administrateur avec `POST /api/v1/utilisateurs` |

Exemple pour créer les deux comptes de démonstration (remplacer `<JETON_ADMIN>` par le jeton
obtenu avec `POST /api/v1/auth/login`) :

```bash
curl -X POST http://localhost:8000/api/v1/utilisateurs \
  -H "Authorization: Bearer <JETON_ADMIN>" -H "Content-Type: application/json" \
  -d '{"email": "accueil@atelier.sn", "nom_complet": "Awa Accueil", "mot_de_passe": "accueil-2026", "role": "accueil"}'

curl -X POST http://localhost:8000/api/v1/utilisateurs \
  -H "Authorization: Bearer <JETON_ADMIN>" -H "Content-Type: application/json" \
  -d '{"email": "tailleur@atelier.sn", "nom_complet": "Moussa Tailleur", "mot_de_passe": "tailleur-2026", "role": "tailleur"}'
```

| Rôle | E-mail | Mot de passe |
|---|---|---|
| admin | valeur de `ADMIN_EMAIL` | valeur de `ADMIN_PASSWORD` |
| accueil | `accueil@atelier.sn` | `accueil-2026` |
| tailleur | `tailleur@atelier.sn` | `tailleur-2026` |

Connexion : `POST /api/v1/auth/login` en formulaire OAuth2 (`username` = e-mail, `password`).
La réponse contient `access_token`, `token_type` et `expires_in`, en secondes.

## Lancer les tests

```bash
pytest -q
```

Les tests tournent sur SQLite en mémoire : ils n'ont besoin ni de PostgreSQL ni du fichier `.env`.
Ils couvrent :

- chaque règle de gestion RG1 à RG24 ;
- les droits de chaque rôle (admin, accueil, tailleur, sans jeton) sur toutes les routes ;
- le **scénario de démonstration de l'annexe A** de bout en bout ([tests/test_scenario_annexe_a.py](tests/test_scenario_annexe_a.py)).

## Architecture

```
app/
├── main.py            # application FastAPI, routeurs, /health
├── config.py          # configuration lue depuis .env (pydantic-settings)
├── database.py        # moteur SQLAlchemy, session, Base
├── security.py        # Argon2 + JWT
├── dependencies.py    # utilisateur connecté, contrôle des rôles, pagination
├── exceptions.py      # exceptions métier (404, 409, 422, 403, 401)
├── errors.py          # conversion des erreurs en {"detail": "..."} en français
├── seed.py            # python -m app.seed
├── models/            # modèles SQLAlchemy (tables)
├── schemas/           # schémas Pydantic Create / Update / Read
├── services/          # TOUTE la logique métier (règles RG1 à RG24)
└── routers/           # un fichier par domaine : droits + appel du service + commit
alembic/               # migrations
tests/                 # pytest
```

Le trajet d'une requête :

1. le **schéma Pydantic** valide le corps (sinon 422) ;
2. le **routeur** vérifie le jeton et le rôle (sinon 401 ou 403), appelle le **service**, puis valide la transaction ;
3. le **service** applique les règles de gestion et lève une exception métier en cas de violation ;
4. cette exception est convertie en `{"detail": "..."}` avec le bon code HTTP.

Les routes ne contiennent aucune règle de gestion, et un modèle de base n'est jamais renvoyé tel quel
(le hash du mot de passe ne sort jamais de l'API).

## Routes réalisées

Les 44 routes de l'énoncé sont réalisées. Légende des rôles : **Tous** = tout utilisateur connecté ; l'administrateur est autorisé partout.

### Authentification et utilisateurs

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 1 | POST | `/auth/login` | Public |
| 2 | GET | `/auth/me` | Tous |
| 3 | POST | `/utilisateurs` | Admin |
| 4 | GET | `/utilisateurs` | Admin |
| 5 | GET | `/utilisateurs/{id}` | Admin |
| 6 | PATCH | `/utilisateurs/{id}` | Admin |

### Clients et catalogue

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 7 | POST | `/clients` | Tous |
| 8 | GET | `/clients` (`q`, `genre`, `limit`, `offset`) | Tous |
| 9 | GET | `/clients/{id}` | Tous |
| 10 | PATCH | `/clients/{id}` | Tous |
| 11 | DELETE | `/clients/{id}` | Admin |
| 12 | GET | `/clients/{id}/commandes` | Tous |
| 13 | GET | `/clients/{id}/resume` | Tous |
| 14 | POST | `/catalogue` | Admin |
| 15 | GET | `/catalogue` (`actifs_seulement`) | Tous |
| 16 | GET | `/catalogue/{id}` | Tous |
| 17 | PATCH | `/catalogue/{id}` | Admin |

### Mesures

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 18 | POST | `/clients/{id}/mesures` | Tailleur |
| 19 | GET | `/clients/{id}/mesures` | Tous |
| 20 | GET | `/clients/{id}/mesures/derniere` | Tous |
| 21 | GET | `/mesures/{id}` | Tous |
| 22 | PATCH | `/mesures/{id}` | Tailleur |
| 23 | DELETE | `/mesures/{id}` | Tailleur |

### Commandes et paiements

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 24 | POST | `/commandes` | Accueil |
| 25 | GET | `/commandes` (`statut`, `client_id`, `en_retard`, `date_min`, `date_max`, `numero`) | Tous |
| 26 | GET | `/commandes/{id}` | Tous |
| 27 | PATCH | `/commandes/{id}` | Accueil |
| 28 | POST | `/commandes/{id}/statut` | Tous (le tailleur ne peut pas annuler) |
| 29 | GET | `/commandes/{id}/historique` | Tous |
| 30 | POST | `/commandes/{id}/lignes` | Accueil |
| 31 | DELETE | `/commandes/{id}/lignes/{ligne_id}` | Accueil |
| 32 | POST | `/commandes/{id}/paiements` | Accueil |
| 33 | GET | `/commandes/{id}/paiements` | Tous |
| 34 | DELETE | `/paiements/{id}` | Admin |

### Livraisons

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 35 | PUT | `/commandes/{id}/livraison` | Accueil |
| 36 | GET | `/commandes/{id}/livraison` | Tous |
| 37 | POST | `/commandes/{id}/livraison/confirmer` | Accueil |
| 38 | GET | `/livraisons` (`statut`, `date_min`, `date_max`) | Tous |

### Statistiques et santé

| N° | Méthode | Chemin | Rôle |
|---|---|---|---|
| 39 | GET | `/statistiques/tableau-de-bord` | Admin |
| 40 | GET | `/statistiques/chiffre-affaires` (`granularite` = jour ou mois, `date_debut`, `date_fin`) | Admin |
| 41 | GET | `/statistiques/types-vetement` (`date_debut`, `date_fin`) | Admin |
| 42 | GET | `/statistiques/top-clients` (`date_debut`, `date_fin`, `limite`) | Admin |
| 43 | GET | `/statistiques/impayes` | Admin |
| 44 | GET | `/health` (hors préfixe) | Public |

Sans dates, les statistiques portent sur la période allant du 1er du mois courant à aujourd'hui.

## Règles de gestion

| Règle | Où elle est appliquée |
|---|---|
| RG1 téléphone unique et normalisé | `services/telephone.py`, `services/clients.py` |
| RG2 à RG4 mesures | `schemas/mesure.py`, `services/mesures.py`, `services/clients.py` |
| RG5 à RG12 commandes et montants | `services/commandes.py` |
| RG13 à RG15 workflow et historique | `services/workflow.py`, `services/commandes.py` |
| RG16, RG17 paiements | `services/paiements.py` |
| RG18 à RG20 livraisons | `services/livraisons.py` |
| RG21 à RG23 sécurité | `security.py`, `dependencies.py`, `services/auth.py` |
| RG24 l'admin ne peut ni se désactiver ni perdre son rôle | `services/utilisateurs.py` |

Workflow des statuts (`POST /commandes/{id}/statut`) :

| Statut actuel | Statuts possibles ensuite |
|---|---|
| `en_attente` | `en_coupe`, `annulee` |
| `en_coupe` | `en_couture`, `annulee` |
| `en_couture` | `essayage`, `terminee`, `annulee` |
| `essayage` | `retouches`, `terminee`, `annulee` |
| `retouches` | `essayage`, `terminee`, `annulee` |
| `terminee` | `livree`, uniquement par `POST /commandes/{id}/livraison/confirmer` |
| `livree`, `annulee` | aucun (statuts finaux) |

## Conventions de l'API

- Erreurs : `{"detail": "message en français"}`. Par exemple :
  `Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe.`
- Listes paginées : `{"items": [...], "total": n, "limit": n, "offset": n}`, avec `limit` à 20 par défaut (100 au maximum) et `offset` à 0.
- `PATCH` ne modifie que les champs envoyés.
- Montants en FCFA (entiers) ; mesures en centimètres.

| Code | Usage |
|---|---|
| 200 / 201 / 204 | Lecture ou modification / création / suppression |
| 401 | Pas de jeton, jeton invalide ou expiré, identifiants incorrects, compte désactivé |
| 403 | Rôle insuffisant |
| 404 | Ressource introuvable |
| 409 | Conflit : doublon, transition interdite, paiement supérieur au solde, ressource utilisée… |
| 422 | Données invalides ou valeur interdite par une règle de gestion |
| 503 | `/health` : la base de données ne répond pas |
