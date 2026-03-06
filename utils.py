"""
Fonctions génériques pour optimiser le backend.
Centralise: upload, URLs médias, validation, parsing.
"""
from pathlib import Path
from typing import Optional, Any, Dict, List
import json
import shutil
import uuid

# Base du backend (parent du dossier contenant utils.py)
_BACKEND_DIR = Path(__file__).resolve().parent
UPLOAD_BASE = _BACKEND_DIR / "uploads"

# Extensions par type MIME (réutilisable partout)
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


# ----- Upload / Fichiers -----


def is_upload_file(value: Any) -> bool:
    """Vérifier si la valeur est un fichier uploadé (FastAPI UploadFile)."""
    return hasattr(value, "file") and hasattr(value, "filename")


def get_upload_extension(
    upload_file: Any,
    content_type_map: Optional[Dict[str, str]] = None,
) -> str:
    """Obtenir l'extension du fichier uploadé (suffix ou depuis content-type)."""
    if upload_file is None:
        return ""
    ext = Path(getattr(upload_file, "filename", None) or "").suffix
    if ext:
        return ext
    mime = getattr(upload_file, "content_type", None) or ""
    return (content_type_map or CONTENT_TYPE_EXTENSIONS).get(mime, "")


def save_upload_file(
    upload_file: Any,
    subdir: str,
    prefix: str = "file",
    content_type_map: Optional[Dict[str, str]] = None,
) -> str:
    """
    Enregistrer un fichier uploadé dans uploads/{subdir}/.
    Retourne le chemin relatif (ex: uploads/orders/order_abc.jpg).
    """
    if not is_upload_file(upload_file):
        raise ValueError("Not an upload file")
    folder = UPLOAD_BASE / subdir
    folder.mkdir(parents=True, exist_ok=True)
    ext = get_upload_extension(upload_file, content_type_map)
    filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
    path = folder / filename
    with path.open("wb") as f:
        upload_file.file.seek(0)
        shutil.copyfileobj(upload_file.file, f)
    return f"uploads/{subdir}/{filename}"


def find_upload_in_form(form: Any, keys: Optional[List[str]] = None) -> Any:
    """
    Chercher un fichier uploadé dans un formulaire (form.get ou form.getlist).
    keys: noms de champs à essayer (défaut: photo, image, file, ...).
    """
    default_keys = (
        "photo", "photo_file", "file", "image", "image_file",
        "photo[]", "image[]", "photo_path", "photoPath", "photoFile",
        "imagePath", "imageFile", "files", "upload", "icon",
    )
    keys = keys or default_keys
    file = form.get("photo") or form.get("photo_file") or form.get("file") or form.get("image")
    if isinstance(file, list):
        file = file[0] if file else None
    if is_upload_file(file):
        return file
    for key in keys:
        for val in form.getlist(key):
            if is_upload_file(val):
                return val
    for _, val in form.multi_items():
        if is_upload_file(val):
            return val
    return None


# ----- URLs médias -----


def build_media_url(
    request: Any,
    path: Optional[str],
    subdir: str,
    check_exists: bool = True,
) -> Optional[str]:
    """
    Construire l'URL absolue d'un fichier média.
    - path: chemin relatif ou nom de fichier (ex: uploads/orders/xx.jpg ou xx.jpg)
    - subdir: sous-dossier dans uploads (ex: orders, designs, categories)
    - check_exists: si True, retourne None si le fichier n'existe pas sur disque
    """
    if not path or not str(path).strip():
        return None
    path = str(path).strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith("images/"):
        path = f"uploads/{subdir}/{Path(path).name}"
    elif not path.startswith("uploads/"):
        if "/" not in path and "\\" not in path:
            path = f"uploads/{subdir}/{path}"
        else:
            path = f"uploads/{subdir}/{Path(path).name}"
    if check_exists:
        full_path = _BACKEND_DIR.parent / path if not path.startswith("uploads") else _BACKEND_DIR / path
        if not full_path.exists():
            return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def normalize_media_attr(
    obj: Any,
    attr_name: str,
    request: Any,
    subdir: str,
    check_exists: bool = True,
) -> None:
    """Modifier en place l'attribut d'un objet pour y mettre l'URL complète du média."""
    if obj is None:
        return
    path = getattr(obj, attr_name, None)
    if not path:
        return
    url = build_media_url(request, path, subdir, check_exists=check_exists)
    if url is not None:
        setattr(obj, attr_name, url)


# ----- Validation / Parsing -----


def parse_bool(value: Any) -> Optional[bool]:
    """Parser une valeur (form/query/body) en booléen."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("true", "1", "yes", "on", "oui"):
        return True
    if s in ("false", "0", "no", "off", "non"):
        return False
    return None


def form_str(value: Any, exclude_upload: bool = True) -> str:
    """Extraire une chaîne depuis un champ formulaire (en ignorant les fichiers)."""
    if value is None:
        return ""
    if exclude_upload and is_upload_file(value):
        return ""
    try:
        return str(value).strip()
    except (AttributeError, TypeError):
        return ""


def validate_json_list(s: Optional[str], allow_empty: bool = True) -> bool:
    """Valider qu'une chaîne est un JSON liste (ou dict) valide pour items."""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    if not s:
        return False
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return allow_empty or len(parsed) > 0 and all(isinstance(x, dict) for x in parsed)
        if isinstance(parsed, dict):
            return True
        return False
    except (json.JSONDecodeError, TypeError, ValueError):
        return False


def parse_json_list(s: Optional[str]) -> List[dict]:
    """Parser une chaîne JSON en liste de dicts."""
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            return [parsed]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def parse_json_list_or_badges(s: Optional[str]) -> Optional[List[str]]:
    """Parser badges / liste JSON (pour packs). Retourne liste de strings ou None."""
    if not s or not str(s).strip():
        return None
    if isinstance(s, list):
        return s
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
        return None
    except (json.JSONDecodeError, TypeError):
        return [x.strip() for x in str(s).split(",") if x.strip()] or None
