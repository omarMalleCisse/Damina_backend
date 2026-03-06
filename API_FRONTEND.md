# API Backend – Guide pour le frontend

Base URL : `http://localhost:8000` (ou l’URL de ton backend).

---

## Authentification

Toutes les requêtes protégées : envoyer le token dans le header :
```http
Authorization: Bearer <access_token>
```

### Auth

| Méthode | URL | Body | Réponse |
|--------|-----|------|--------|
| POST | `/api/auth/register` | `{ "username", "email", "phone", "address", "password" }` | `User` |
| POST | `/api/auth/login` | **form-data** : `username` (email), `password` | `{ "access_token", "token_type": "bearer" }` |
| POST | `/api/auth/logout` | - | `{ "message" }` |
| GET | `/api/auth/me` | - (Bearer requis) | `User` |

---

## Designs

| Méthode | URL | Query / Body | Réponse |
|--------|-----|--------------|--------|
| GET | `/api/designs` | `?filter=all\|free\|premium\|popular` `&category=` `&page=1` `&limit=12` | `{ items, total, page, limit, total_pages }` |
| GET | `/api/designs/{design_id}` | - | `Design` |
| POST | `/api/designs` | **multipart** : `title`, `description`, `price`, `is_premium`, `category_ids[]`, `image`, **`download_files`** (plusieurs fichiers DST/JEF/PES…) | `Design` |
| PUT | `/api/designs/{design_id}` | **multipart** ou **JSON** : champs à modifier + `download_files` (fichiers ou liste de chemins) | `Design` |
| DELETE | `/api/designs/{design_id}` | - | 204 |
| POST | `/api/designs/{design_id}/download` | - (Bearer requis) | `Design` (compteur incrémenté) |

**Design (réponse)** :
```json
{
  "id": 1,
  "title": "string",
  "description": "string | null",
  "price": "string | null",
  "is_premium": false,
  "download_count": 0,
  "downloads": "string | null",
  "image_path": "http://.../uploads/designs/xxx.jpg",
  "download_files": ["http://.../uploads/designs/files/xxx.dst", "http://.../uploads/designs/files/xxx.jef"],
  "categories": [{ "id", "name", "icon" }]
}
```

**Formats broderie acceptés pour `download_files`** : `.dst`, `.jef`, `.pes`, `.pec`, `.hus`, `.vip`, `.vp3`, `.sew`, `.xxx`, `.exp`, `.pcs`, `.psc`, `.emd`, `.phc`, `.shv`.

---

## Catégories

| Méthode | URL | Body | Réponse |
|--------|-----|------|--------|
| GET | `/api/categories` | - | `[Category]` |
| GET | `/api/categories/{category_id}` | - | `Category` |
| POST | `/api/categories` | **multipart** : `name`, `icon` (fichier) ou `icon_url` | `Category` |
| PUT | `/api/categories/{category_id}` | multipart / JSON | `Category` |
| DELETE | `/api/categories/{category_id}` | - | 204 |

**Métadonnées (public)**  
- GET `/api/filters` → liste des filtres  
- GET `/api/features` → liste des features  

---

## Packs

| Méthode | URL | Body | Réponse |
|--------|-----|------|--------|
| GET | `/api/packs` | - | `[Pack]` |
| GET | `/api/packs/{pack_id}` | - | `Pack` |
| GET | `/api/packs/{pack_id}/commandes` | - (Bearer **admin**) | `[Order]` |
| POST | `/api/packs` | **form** : `title`, `subtitle`, `delivery`, `price`, `cta_label`, `cta_to`, `badges` (JSON ou CSV) | `Pack` |
| PUT | `/api/packs/{pack_id}` | form / JSON | `Pack` |
| DELETE | `/api/packs/{pack_id}` | - | 204 |

---

## Commandes pack (pack-orders)

**Authentification requise.** Admin voit tout ; client voit ses commandes.

| Méthode | URL | Query / Body | Réponse |
|--------|-----|--------------|--------|
| GET | `/api/pack-orders` | `?pack_id=` `?user_id=` (admin) `?is_done=` `?skip=` `?limit=` | `[PackOrder]` (avec `pack` et `user`) |
| GET | `/api/pack-orders/{pack_order_id}` | - | `PackOrder` |
| POST | `/api/pack-orders` | **multipart** ou **JSON** : `pack_id`, `customer_name`, `customer_email`, `customer_phone`, `customer_address`, `items` (JSON), `quantity`, `notes`, `description`, `photo` (fichier) | `PackOrder` |
| PUT | `/api/pack-orders/{pack_order_id}` | JSON : `quantity`, `status`, `is_done`, `notes`, … | `PackOrder` |
| DELETE | `/api/pack-orders/{pack_order_id}` | - | 204 |

**PackOrder** : `id`, `user_id`, `pack_id`, `quantity`, `customer_name`, `customer_email`, `customer_phone`, `customer_address`, `items`, `notes`, `description`, `photo_url`, `status`, `is_done`, `created_at`, `updated_at`, `pack`, `user`.

---

## Commandes (orders)

| Méthode | URL | Query / Body | Réponse |
|--------|-----|--------------|--------|
| GET | `/api/orders` | `?status=` `?is_done=` `?skip=` `?limit=` (auth : user ou admin) | `[Order]` |
| GET | `/api/orders/{order_id}` | - | `Order` |
| POST | `/api/orders` | **multipart** ou **JSON** : `customer_name`, `customer_email`, `customer_phone`, `customer_address`, `items` (JSON), `notes`, `photo` (fichier) | `Order` |
| PUT | `/api/orders/{order_id}` | multipart / JSON (+ `is_done`) | `Order` |
| PATCH | `/api/orders/{order_id}/done` | `?is_done=true` (défaut) ou `false` (Bearer) | `Order` |
| DELETE | `/api/orders/{order_id}` | - (Bearer **admin**) | 204 |

**Order** : `id`, `user_id`, `customer_name`, `customer_email`, `customer_phone`, `customer_address`, `items`, `photo_url`, `status`, `is_done`, `notes`, `created_at`, `updated_at`.

**Exemple `items`** : `[{"title": "Design 1", "quantity": 2}, {"pack_id": 1, "title": "Pack USB", "quantity": 1}]`

---

## Panier (cart)

Header optionnel : `X-Cart-Id: <id>` pour lier la session au panier.

| Méthode | URL | Body | Réponse |
|--------|-----|------|--------|
| GET | `/api/cart` | `?cart_id=` ou header `X-Cart-Id` | `Cart` (réponse inclut header `X-Cart-Id`) |
| POST | `/api/cart/items` | `{ "design_id": 1, "quantity": 1 }` | `Cart` |
| PUT | `/api/cart/items/{item_id}` | `{ "quantity": 2 }` | `Cart` |
| DELETE | `/api/cart/items/{item_id}` | - | `Cart` |
| DELETE | `/api/cart/clear` | - | `Cart` |

**Cart** : `id`, `user_id`, `created_at`, `updated_at`, `items` (avec `design` et `quantity`).

---

## Utilisateurs (admin)

**Authentification admin requise** pour liste / suppression ; chaque user peut GET/PUT son propre profil.

| Méthode | URL | Body | Réponse |
|--------|-----|------|--------|
| GET | `/api/users` | - (admin) | `[User]` |
| GET | `/api/users/{user_id}` | - | `User` |
| PUT | `/api/users/{user_id}` | `{ "username", "email", "phone", "address", "password?" }` | `User` |
| DELETE | `/api/users/{user_id}` | - (admin ou soi-même) | 204 |

---

## Features (admin)

Toutes les routes nécessitent **Bearer + admin**.

| Méthode | URL | Body | Réponse |
|--------|-----|------|--------|
| GET | `/api/admin/features` | - | `[Feature]` |
| GET | `/api/admin/features/{feature_id}` | - | `Feature` |
| POST | `/api/admin/features` | `{ "title", "description?" }` | `Feature` |
| PUT | `/api/admin/features/{feature_id}` | `{ "title?", "description?" }` | `Feature` |
| DELETE | `/api/admin/features/{feature_id}` | - | 204 |

---

## Téléchargements

| Méthode | URL | Query | Réponse |
|--------|-----|-------|--------|
| GET | `/api/downloads` | `?design_id=` `?user_id=` `?page=` `?limit=` (Bearer) | `[Download]` |

---

## Fichiers statiques

- Images designs : `<base_url>/uploads/designs/<filename>`
- Fichiers broderie : `<base_url>/uploads/designs/files/<filename>`
- Catégories : `<base_url>/uploads/categories/<filename>`
- Packs : `<base_url>/uploads/packs/<filename>`
- Commandes : `<base_url>/uploads/orders/<filename>`
- Pack orders : `<base_url>/uploads/pack_orders/<filename>`

Les réponses API renvoient déjà ces URLs complètes quand c’est le cas (ex. `image_path`, `download_files`, `photo_url`).

---

## CORS

Origines autorisées par défaut : `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, `http://127.0.0.1:5173`.  
À adapter dans `backend/config.py` si ton front tourne ailleurs.

---

## Récap pour le front

1. **Login** : `POST /api/auth/login` (form-data `username` = email, `password`) → stocker `access_token`.
2. **Requêtes protégées** : header `Authorization: Bearer <access_token>`.
3. **Designs** : pagination avec `page` / `limit` ; création avec `image` + `download_files` (plusieurs fichiers) en multipart.
4. **Panier** : conserver le `X-Cart-Id` renvoyé par le serveur pour les appels suivants.
5. **Commandes** : `items` en JSON string ou tableau ; `is_done` pour marquer terminé.
6. **Admin** : utiliser les routes `/api/admin/features` et les DELETE/GET list sur users/orders/pack-orders quand l’utilisateur est admin.
