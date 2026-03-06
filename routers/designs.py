from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request, Path as PathParam, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid

# Imports absolus au lieu d'imports relatifs
import auth
import crud
import models
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/designs", tags=["designs"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "designs"
FILES_DIR = UPLOAD_DIR / "files"  # Fichiers broderie (DST, JEF, PES...)
_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
# Extensions autorisées pour les fichiers à télécharger (formats broderie)
EMBROIDERY_EXTENSIONS = {".dst", ".jef", ".pes", ".pec", ".hus", ".vip", ".vp3", ".sew", ".xxx", ".exp", ".pcs", ".psc", ".emd", ".phc", ".shv"}


def _build_image_url(request: Request, image_path: Optional[str]) -> Optional[str]:
    if not image_path:
        return None
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path
    file_path = None
    if image_path.startswith("images/"):
        image_path = f"uploads/designs/{Path(image_path).name}"
        file_path = UPLOAD_DIR / Path(image_path).name
    elif image_path.startswith("uploads/"):
        file_path = Path(__file__).resolve().parent.parent / image_path
    elif "/" not in image_path and "\\" not in image_path:
        image_path = f"uploads/designs/{image_path}"
        file_path = UPLOAD_DIR / Path(image_path).name

    if file_path and not file_path.exists():
        return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/{image_path.lstrip('/')}"


def _normalize_design_image(request: Request, design: models.Design) -> None:
    if design and getattr(design, "image_path", None):
        design.image_path = _build_image_url(request, design.image_path)


def _normalize_design_download_files(request: Request, design: models.Design) -> None:
    """Convertir les chemins des fichiers broderie en URLs complètes."""
    if not design or not getattr(design, "download_files", None):
        return
    files = design.download_files
    if not isinstance(files, list):
        return
    base = str(request.base_url).rstrip("/")
    result = []
    for path in files:
        if not path:
            continue
        if isinstance(path, str) and (path.startswith("http://") or path.startswith("https://")):
            result.append(path)
        else:
            result.append(f"{base}/{str(path).lstrip('/')}")
    design.download_files = result


def _normalize_design_images(request: Request, design: models.Design) -> None:
    """Convertir les chemins des images (liste) en URLs complètes."""
    if not design or not getattr(design, "images", None):
        return
    images = design.images
    if not isinstance(images, list):
        return
    base = str(request.base_url).rstrip("/")
    result = []
    for path in images:
        if not path:
            continue
        if isinstance(path, str) and (path.startswith("http://") or path.startswith("https://")):
            result.append(path)
        else:
            result.append(f"{base}/{str(path).lstrip('/')}")
    design.images = result


def _get_embroidery_extension(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    return ext if ext in EMBROIDERY_EXTENSIONS else ""


def _sanitize_design_filename(title: Optional[str]) -> str:
    """Convertit le titre du design en base de nom de fichier (sans extension)."""
    if not title or not str(title).strip():
        return "design"
    s = str(title).strip()
    # Remplacer espaces et caractères indésirables par _
    parts = []
    for c in s:
        if c.isalnum() or c in "._-":
            parts.append(c)
        elif c.isspace() or c in "-–—":
            if parts and parts[-1] != "_":
                parts.append("_")
        # sinon on ignore le caractère
    base = "".join(parts).strip("_.") or "design"
    return base[:80]  # limite de longueur


def _save_embroidery_files(
    upload_files: list,
    design_prefix: str,
    design_name: Optional[str] = None,
) -> List[str]:
    """Enregistre les fichiers broderie et retourne la liste des chemins relatifs.
    Si design_name est fourni (ex. titre du design), les fichiers sont nommés comme le design (ex. Mon_Design.dst).
    """
    if not upload_files:
        return []
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    base = _sanitize_design_filename(design_name) if design_name else design_prefix
    paths = []
    for i, f in enumerate(upload_files):
        if not (hasattr(f, "file") and hasattr(f, "filename")):
            continue
        ext = _get_embroidery_extension(f.filename or "")
        if not ext:
            continue
        if i == 0:
            name = f"{base}{ext}"
        else:
            name = f"{base}_{i + 1}{ext}"
        # Éviter doublon : si le fichier existe déjà, ajouter un suffixe unique
        path = FILES_DIR / name
        if path.exists():
            name = f"{base}_{uuid.uuid4().hex[:8]}{ext}"
            path = FILES_DIR / name
        with path.open("wb") as buffer:
            f.file.seek(0)
            shutil.copyfileobj(f.file, buffer)
        paths.append(f"uploads/designs/files/{name}")
    return paths


def _get_upload_extension(image: UploadFile) -> str:
    extension = Path(image.filename or "").suffix
    if extension:
        return extension
    return _CONTENT_TYPE_EXTENSIONS.get(image.content_type or "", "")


def _is_upload_file(value: object) -> bool:
    return hasattr(value, "file") and hasattr(value, "filename")


@router.get("/protected")
def protected_example(current_user=Depends(auth.get_current_user)):
    """Exemple de route protégée."""
    return {
        "message": "Accès autorisé",
        "user_id": current_user.id,
        "email": current_user.email,
    }


@router.get("", response_model=schemas.PaginatedDesignsResponse)
def list_designs(
    filter: Optional[str] = "all",
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 12,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Récupérer les designs avec pagination (12 par page par défaut).

    - **filter**: "all", "free", "premium", "popular"
    - **category**: ID ou nom de la catégorie
    - **page**: numéro de page (1-based)
    - **limit**: nombre de designs par page (défaut 12)
    """
    if page < 1:
        page = 1
    if limit < 1:
        limit = 12
    if limit > 100:
        limit = 100
    skip = (page - 1) * limit
    total = crud.get_designs_count(db, filter=filter, category=category)
    designs = crud.get_designs(db, filter=filter, category=category, skip=skip, limit=limit)
    if request:
        for design in designs:
            _normalize_design_image(request, design)
            _normalize_design_images(request, design)
            _normalize_design_download_files(request, design)
    total_pages = (total + limit - 1) // limit if limit else 1
    return schemas.PaginatedDesignsResponse(
        items=designs,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{design_id}", response_model=schemas.DesignResponse)
def get_design(design_id: int, request: Request, db: Session = Depends(get_db)):
    """Récupérer un design spécifique par ID."""
    design = crud.get_design_by_id(db, design_id)
    if not design:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design non trouvé")
    _normalize_design_image(request, design)
    _normalize_design_images(request, design)
    _normalize_design_download_files(request, design)
    return design


def _save_design_images(upload_images: list) -> List[str]:
    """Enregistre les images et retourne la liste des chemins relatifs."""
    if not upload_images:
        return []
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for img in upload_images:
        if not _is_upload_file(img) or not (img.filename or "").strip():
            continue
        ext = _get_upload_extension(img)
        if not ext:
            continue
        filename = f"design_{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / filename
        with file_path.open("wb") as buffer:
            img.file.seek(0)
            shutil.copyfileobj(img.file, buffer)
        paths.append(f"uploads/designs/{filename}")
    return paths


@router.post("", response_model=schemas.DesignResponse, status_code=status.HTTP_201_CREATED)
def create_design(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    price: Optional[str] = Form(None),
    is_premium: bool = Form(False),
    category_ids: Optional[List[int]] = Form(None),
    image: Optional[UploadFile] = File(None),
    images: Optional[List[UploadFile]] = File(None),
    download_files: Optional[List[UploadFile]] = File(None),
    longueur: Optional[int] = Form(None),
    largeur: Optional[int] = Form(None),
    color: Optional[int] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Créer un nouveau design avec une ou plusieurs images et fichiers broderie (DST, JEF, PES...)."""
    image_path = None
    image_paths = []
    if image and _is_upload_file(image):
        image_paths = _save_design_images([image])
        if image_paths:
            image_path = image_paths[0]
    if images:
        image_paths = image_paths + _save_design_images([f for f in images if _is_upload_file(f)])
        if not image_path and image_paths:
            image_path = image_paths[0]

    download_file_paths = []
    if download_files:
        download_file_paths = _save_embroidery_files(download_files, "design", design_name=title)

    design_in = schemas.DesignCreate(
        title=title,
        description=description,
        price=price,
        is_premium=is_premium,
        image_path=image_path,
        images=image_paths if image_paths else None,
        category_ids=category_ids,
        download_files=download_file_paths if download_file_paths else None,
        longueur=longueur,
        largeur=largeur,
        color=color,
    )
    design = crud.create_design(db, design_in)
    if request:
        _normalize_design_image(request, design)
        _normalize_design_images(request, design)
        _normalize_design_download_files(request, design)
    return design


def _parse_bool(value: Optional[object]) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    return None


@router.put("/{design_id}", response_model=schemas.DesignResponse)
async def update_design(design_id: int, request: Request, db: Session = Depends(get_db)):
    """Mettre à jour un design existant (JSON ou multipart)."""
    content_type = (request.headers.get("content-type") or "").lower()
    data = {}

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        title = form.get("title")
        description = form.get("description")
        price = form.get("price")
        is_premium = _parse_bool(form.get("is_premium"))
        category_ids = form.getlist("category_ids")
        image = form.get("image") or form.get("image_file") or form.get("file")
        if isinstance(image, list):
            image = image[0] if image else None
        if not _is_upload_file(image):
            for key in ("image", "image_file", "file", "image[]", "image_path", "imagePath", "imageFile", "files", "upload"):
                for value in form.getlist(key):
                    if _is_upload_file(value):
                        image = value
                        break
                if _is_upload_file(image):
                    break
        if not _is_upload_file(image):
            for _, value in form.multi_items():
                if _is_upload_file(value):
                    image = value
                    break

        if title is not None and title != "":
            data["title"] = title
        if description is not None and description != "":
            data["description"] = description
        if price is not None and price != "":
            data["price"] = price
        if is_premium is not None:
            data["is_premium"] = is_premium
        if category_ids:
            cleaned_ids = []
            for value in category_ids:
                if value is None or str(value).strip() == "":
                    continue
                cleaned_ids.append(int(value))
            if cleaned_ids:
                data["category_ids"] = cleaned_ids

        # Champs longueur, largeur, color
        longueur_val = form.get("longueur")
        if longueur_val is not None and str(longueur_val).strip() != "":
            try:
                # Convertir en float puis en int pour gérer les décimales
                data["longueur"] = int(float(longueur_val))
            except (ValueError, TypeError):
                pass

        largeur_val = form.get("largeur")
        if largeur_val is not None and str(largeur_val).strip() != "":
            try:
                # Convertir en float puis en int pour gérer les décimales
                data["largeur"] = int(float(largeur_val))
            except (ValueError, TypeError):
                pass

        color_val = form.get("color")
        if color_val is not None and str(color_val).strip() != "":
            try:
                # Convertir en float puis en int pour gérer les décimales
                data["color"] = int(float(color_val))
            except (ValueError, TypeError):
                pass

        # Ne remplacer l'image que si un vrai fichier image est envoyé (jpg/png/webp/gif), avec du contenu
        _IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if _is_upload_file(image) and (image.filename or "").strip():
            extension = _get_upload_extension(image)
            if extension and extension.lower() in _IMAGE_EXTENSIONS:
                try:
                    image.file.seek(0)
                    content = image.file.read()
                    image.file.seek(0)
                except Exception:
                    content = b""
                if len(content) > 0:
                    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                    filename = f"design_{uuid.uuid4().hex}{extension}"
                    file_path = UPLOAD_DIR / filename
                    file_path.write_bytes(content)
                    data["image_path"] = f"uploads/designs/{filename}"

        # Images supplémentaires (plusieurs images) — ignorer les fichiers vides
        extra_images = []
        for key in form.keys():
            if key in ("images", "images[]", "image[]"):
                for value in form.getlist(key):
                    if _is_upload_file(value) and (value.filename or "").strip():
                        extra_images.append(value)
        if extra_images:
            new_image_paths = _save_design_images(extra_images)
            existing = crud.get_design_by_id(db, design_id)
            existing_images = list(existing.images) if (existing and getattr(existing, "images", None)) else []
            data["images"] = existing_images + new_image_paths

        # Fichiers broderie (plusieurs fichiers possibles)
        extra_files = []
        for key in form.keys():
            if key in ("download_files", "download_files[]", "files", "broderie"):
                for value in form.getlist(key):
                    if _is_upload_file(value):
                        extra_files.append(value)
        if extra_files:
            existing = crud.get_design_by_id(db, design_id)
            design_title = existing.title if existing else None
            new_paths = _save_embroidery_files(extra_files, "design", design_name=design_title)
            existing_files = list(existing.download_files) if (existing and getattr(existing, "download_files", None)) else []
            data["download_files"] = existing_files + new_paths
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            # Ne pas écraser l'image existante si image_path/images sont vides
            body = {
                k: v for k, v in body.items()
                if k not in ("image_path", "images")
                or (v is not None and v != "" and (not isinstance(v, list) or len(v) > 0))
            }
            # Convertir les valeurs décimales en entiers pour longueur, largeur, color
            for field in ("longueur", "largeur", "color"):
                if field in body and body[field] is not None:
                    try:
                        if isinstance(body[field], (int, float)):
                            body[field] = int(float(body[field]))
                    except (ValueError, TypeError):
                        pass
            data.update(body)

    design_in = schemas.DesignUpdate(**data)
    design = crud.update_design(db, design_id, design_in)
    if not design:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design non trouvé")
    _normalize_design_image(request, design)
    _normalize_design_images(request, design)
    _normalize_design_download_files(request, design)
    return design


@router.delete("/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_design(design_id: int, db: Session = Depends(get_db)):
    """Supprimer un design."""
    ok = crud.delete_design(db, design_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design non trouvé")


@router.post("/{design_id}/download", response_model=schemas.DesignResponse)
def download_design(
    request: Request,
    design_id: int = PathParam(..., gt=0, description="ID du design"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Téléchargement : design gratuit ou après paiement (design premium)."""
    design = crud.get_design_by_id(db, design_id)
    if not design:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design non trouvé")
    if getattr(design, "is_premium", False) and not current_user.is_admin:
        if not crud.has_user_paid_for_design(db, design_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Paiement requis pour ce design premium. Initiez un paiement puis revenez ici.",
            )
    design = crud.increment_download_count(db, design_id)
    if not design:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design non trouvé")
    crud.create_download(db, design_id=design_id, user_id=current_user.id)
    _normalize_design_image(request, design)
    _normalize_design_images(request, design)
    _normalize_design_download_files(request, design)
    return design


def _resolve_design_file_path(relative_path: str) -> Optional[Path]:
    """Retourne le chemin absolu du fichier broderie, ou None si invalide."""
    if not relative_path or not isinstance(relative_path, str):
        return None
    path = relative_path.replace("\\", "/").strip()
    # URL complète : extraire le chemin (ex. /uploads/designs/files/xxx.dst)
    if path.startswith("http://") or path.startswith("https://"):
        try:
            from urllib.parse import urlparse
            parsed = urlparse(path)
            path = parsed.path.lstrip("/")
        except Exception:
            return None
    path = path.lstrip("/")
    if ".." in path:
        return None
    # Fichier dans uploads/designs/files/
    if path.startswith("uploads/designs/files/"):
        backend_root = Path(__file__).resolve().parent.parent
        full = backend_root / path
    else:
        # Juste le nom de fichier (ex. design_abc.dst)
        name = path.split("/")[-1] if "/" in path else path
        if not name or "." not in name:
            return None
        full = FILES_DIR / name
    try:
        full = full.resolve()
        if not full.is_file():
            return None
        # Sécurité : le fichier doit être sous FILES_DIR
        try:
            full.relative_to(FILES_DIR.resolve())
        except ValueError:
            return None
        return full
    except (OSError, RuntimeError):
        return None


def _safe_download_filename(name: str, default_ext: str = ".dst") -> str:
    """Retourne un nom de fichier sûr avec une extension valide (évite 'design-7-0' sans extension)."""
    if not name or not name.strip():
        return "design" + default_ext
    name = name.strip()
    # Supprimer chemin ou URL, garder uniquement le nom
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    if "\\" in name:
        name = name.rsplit("\\", 1)[-1]
    # Supprimer query string
    if "?" in name:
        name = name.split("?")[0]
    # S'assurer qu'il y a une extension connue
    ext = Path(name).suffix.lower()
    if ext not in EMBROIDERY_EXTENSIONS:
        name = name + default_ext if not ext else name.rsplit(".", 1)[0] + default_ext
    # Caractères sûrs uniquement
    safe = "".join(c for c in name if c.isalnum() or c in "._-")
    return safe or "design" + default_ext


@router.get("/{design_id}/files/{file_index}/download")
def download_design_file(
    design_id: int = PathParam(..., gt=0),
    file_index: int = PathParam(..., ge=0),
    filename: Optional[str] = Query(None, description="Nom du fichier pour le téléchargement (ex. design.dst)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Téléchargement direct d'un seul fichier (DST, PES, etc.) — pas de zip.
    Retourne le fichier avec Content-Disposition: attachment.
    Option : ?filename=monfichier.dst pour forcer le nom téléchargé (avec extension).
    """
    design = crud.get_design_by_id(db, design_id)
    if not design:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design non trouvé")
    if getattr(design, "is_premium", False) and not current_user.is_admin:
        if not crud.has_user_paid_for_design(db, design_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Paiement requis pour ce design.",
            )
    files = getattr(design, "download_files", None) or []
    if not isinstance(files, list) or file_index >= len(files):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable.")
    relative = files[file_index]
    if isinstance(relative, dict):
        relative = relative.get("path") or relative.get("url") or ""
    raw = str(relative).strip()
    file_path = _resolve_design_file_path(raw)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable.")
    # Nom pour Content-Disposition : query param > nom du fichier sur disque (toujours avec extension)
    if filename and filename.strip():
        response_filename = _safe_download_filename(filename.strip())
    else:
        response_filename = _safe_download_filename(file_path.name)
    # Lire les octets pour s'assurer d'envoyer le contenu (éviter fichier vide)
    try:
        content = file_path.read_bytes()
    except OSError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable.")
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{response_filename}"',
            "Content-Length": str(len(content)),
        },
    )