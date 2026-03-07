# Déploiement du backend sur Railway

## 1. Prérequis

- Compte [Railway](https://railway.app)
- Projet GitHub (ou CLI) avec le code du backend

## 2. Créer le projet Railway

1. **New Project** → **Deploy from GitHub repo** (ou "Empty Project" + `railway link`).
2. Choisir le dépôt et la branche.

## 3. Configurer le service

### Root Directory (important)

- **Settings** → **Root Directory** : `backend`  
  Ainsi Railway utilise le dossier `backend` (requirements.txt, main.py, Procfile).

### Variables d'environnement

Dans **Variables** du service, ajouter au minimum :

| Variable | Description | Exemple |
|----------|-------------|---------|
| `DATABASE_URL` | URL MySQL (Railway propose un addon MySQL) | `mysql+pymysql://user:pass@host:3306/db` |
| `SECRET_KEY` | Clé JWT (générer une chaîne aléatoire longue) | `votre_secret_tres_long` |
| `FRONTEND_URL` | URL du frontend (pour CORS et redirections) | `https://votre-app.vercel.app` |
| `CORS_ORIGINS` | (Optionnel) Origines CORS séparées par des virgules | `https://votre-app.com` |

Pour PayTech en production :

- `PAYTECH_API_KEY`
- `PAYTECH_SIGNING_KEY`
- `PAYTECH_IPN_URL` = `https://VOTRE-DOMAINE-RAILWAY.up.railway.app/api/payments/webhook`
- `PAYTECH_SANDBOX` = `false`

## 4. Connecter le backend (déjà en prod) à la BDD Railway

Pour que ton **backend déjà déployé** sur Railway utilise la **base MySQL** du même projet :

1. Ouvre ton **projet Railway** (celui où tourne le backend).
2. **Ajoute MySQL** si besoin : **+ New** → **Database** → **MySQL**. Railway crée le service MySQL.
3. **Donne la connexion au backend** : dans le service **backend** → **Variables** → **Add Variable Reference** → choisir le service **MySQL** → sélectionner **MYSQL_URL** (ou **MYSQL_PUBLIC_URL** si le backend n’est pas sur le même réseau privé).
4. **Redéploie** le backend. Il utilisera alors la BDD Railway.
5. **Vérif** : `GET https://ton-backend.up.railway.app/health?db=1` → la DB doit être OK.

Le backend utilise : **`DATABASE_URL`** > **`MYSQL_URL`** > **`MYSQL_PUBLIC_URL`** et convertit `mysql://` en `mysql+pymysql://`. Aucun changement de code.

## 5. Déploiement

- À chaque push sur la branche liée, Railway rebuild et redéploie.
- Ou : **Deploy** manuel depuis le dashboard.

## 6. Domaine public

- **Settings** → **Networking** → **Generate Domain**.
- Utiliser cette URL comme `FRONTEND_URL` côté front si besoin, et surtout comme base pour `PAYTECH_IPN_URL` (ex. `https://xxx.up.railway.app`).

## 7. Vérifications

- **Health** : `GET https://votre-service.up.railway.app/health` → `{"status":"ok"}`
- **API** : `GET https://votre-service.up.railway.app/` → message de bienvenue
- CORS : le frontend doit avoir son URL dans `FRONTEND_URL` ou `CORS_ORIGINS`.

## 8. Fichiers utiles dans `backend/`

- `Procfile` : commande de démarrage avec `$PORT`
- `railway.toml` : start command et politique de redémarrage
- `.env.example` : liste des variables à définir
- `requirements.txt` : dépendances Python pour le build

## 9. Déploiement sans Root Directory

Si tu ne mets pas Root Directory = `backend`, utiliser le **Procfile à la racine du repo** :

```text
web: cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Dans ce cas, s’assurer que les dépendances sont installées depuis la racine (par ex. `requirements.txt` à la racine qui inclut tout, ou config Nixpacks pour installer depuis `backend/`).
