# Fonctions génériques backend

Résumé des modules d’optimisation et de leur usage.

---

## 1. `utils.py` – Upload, URLs, validation

### Upload / Fichiers
| Fonction | Usage |
|----------|--------|
| `is_upload_file(value)` | Savoir si une valeur est un `UploadFile` |
| `get_upload_extension(upload_file, content_type_map=None)` | Récupérer l’extension (suffix ou MIME) |
| `save_upload_file(upload_file, subdir, prefix="file")` | Enregistrer dans `uploads/{subdir}/` et retourner le chemin relatif |
| `find_upload_in_form(form, keys=None)` | Trouver un fichier dans un formulaire (photo, image, file, …) |

### URLs médias
| Fonction | Usage |
|----------|--------|
| `build_media_url(request, path, subdir, check_exists=True)` | Construire l’URL absolue (ex. `subdir="orders"` → `uploads/orders/`) |
| `normalize_media_attr(obj, attr_name, request, subdir)` | Remplacer un attribut (ex. `photo_url`) par l’URL complète |

### Validation / Parsing
| Fonction | Usage |
|----------|--------|
| `parse_bool(value)` | Convertir form/query en `True`/`False`/`None` |
| `form_str(value)` | Lire une chaîne depuis un champ formulaire (sans traiter les fichiers) |
| `validate_json_list(s)` | Vérifier qu’une chaîne est un JSON liste/dict valide |
| `parse_json_list(s)` | Parser une chaîne JSON en liste de dicts |
| `parse_json_list_or_badges(s)` | Parser badges (JSON ou liste séparée par des virgules) |

### Constantes
- `utils.CONTENT_TYPE_EXTENSIONS` : mapping MIME → extension
- `utils.UPLOAD_BASE` : chemin du dossier `uploads/`

---

## 2. `deps.py` – Auth et permissions

| Élément | Usage |
|--------|--------|
| `require_admin` | **Dépendance FastAPI** : utilisateur connecté et admin, sinon 403 |
| `ensure_admin(current_user)` | Lancer 403 si l’utilisateur n’est pas admin |
| `can_access_resource(current_user, resource_user_id)` | `True` si admin ou si `resource_user_id == current_user.id` (ou ressource sans owner) |
| `require_access(current_user, resource_user_id, message)` | Lancer 403 si `can_access_resource` est faux |

### Exemples

```python
# Route réservée aux admins
@router.get("/admin-only")
def admin_route(current_user: models.User = Depends(deps.require_admin)):
    ...

# Vérifier l’accès à une ressource (owner ou admin)
deps.require_access(current_user, order.user_id, "Accès refusé")
```

---

## 3. Routers déjà migrés

- **features** : `deps.require_admin` pour toutes les routes
- **users** : `deps.require_admin` / `deps.ensure_admin`
- **pack_orders** : `utils` (upload, form_str, validate_json_list, normalize_media_attr, save_upload_file), `deps.require_access`
- **packs** : `utils.parse_json_list_or_badges`, `deps.ensure_admin` pour les commandes par pack

---

## 4. Pistes pour le reste du code

- **orders** : remplacer `_is_upload_file`, `_get_upload_extension`, `_build_photo_url`, `_normalize_order_photo`, `_validate_items`, `_parse_bool` par les équivalents dans `utils` (et éventuellement `deps.require_access`).
- **designs** : utiliser `utils.is_upload_file`, `utils.get_upload_extension`, `utils.build_media_url`, `utils.normalize_media_attr`, `utils.save_upload_file`.
- **categories** : idem pour l’icône (subdir `"categories"`).
- **cart** : utiliser `utils.build_media_url` pour les images des designs du panier.

En important `utils` et `deps` dans chaque routeur, on évite de dupliquer la logique d’upload, d’URL et de permissions.
