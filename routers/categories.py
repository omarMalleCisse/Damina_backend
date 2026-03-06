from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
from typing import List, Optional
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid

# Imports absolus
import crud
import models
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/categories", tags=["categories"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "categories"
_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


def _build_icon_url(request: Request, icon_path: Optional[str]) -> Optional[str]:
    """Construire l'URL complète de l'icône."""
    if not icon_path:
        return None
    if icon_path.startswith("http://") or icon_path.startswith("https://"):
        return icon_path
    file_path = None
    if icon_path.startswith("images/"):
        icon_path = f"uploads/categories/{Path(icon_path).name}"
        file_path = UPLOAD_DIR / Path(icon_path).name
    elif icon_path.startswith("uploads/"):
        file_path = Path(__file__).resolve().parent.parent / icon_path
    elif "/" not in icon_path and "\\" not in icon_path:
        icon_path = f"uploads/categories/{icon_path}"
        file_path = UPLOAD_DIR / Path(icon_path).name

    if file_path and not file_path.exists():
        return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/{icon_path.lstrip('/')}"


def _normalize_category_icon(request: Request, category: models.Category) -> None:
    """Normaliser le chemin de l'icône de la catégorie."""
    if category and getattr(category, "icon", None):
        category.icon = _build_icon_url(request, category.icon)


def _get_upload_extension(icon: UploadFile) -> str:
    """Obtenir l'extension du fichier uploadé."""
    extension = Path(icon.filename or "").suffix
    if extension:
        return extension
    return _CONTENT_TYPE_EXTENSIONS.get(icon.content_type or "", "")


def _is_upload_file(value: object) -> bool:
    """Vérifier si la valeur est un fichier uploadé."""
    return hasattr(value, "file") and hasattr(value, "filename")


@router.get("", response_model=List[schemas.CategoryResponse])
def list_categories(request: Request, db: Session = Depends(get_db)):
    """Récupérer toutes les catégories."""
    categories = crud.get_all_categories(db)
    for category in categories:
        _normalize_category_icon(request, category)
    return categories


@router.get("/{category_id}", response_model=schemas.CategoryResponse)
def get_category(category_id: int, request: Request, db: Session = Depends(get_db)):
    """Récupérer une catégorie par ID."""
    category = crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
    _normalize_category_icon(request, category)
    return category


@router.post("", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    name: str = Form(...),
    icon: Optional[UploadFile] = File(None),
    icon_url: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Créer une nouvelle catégorie avec support pour upload d'icône."""
    icon_path = icon_url
    
    # Gérer l'upload de fichier si fourni
    if icon:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        extension = _get_upload_extension(icon)
        filename = f"category_{uuid.uuid4().hex}{extension}"
        file_path = UPLOAD_DIR / filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(icon.file, buffer)
        icon_path = f"uploads/categories/{filename}"

    category_in = schemas.CategoryCreate(
        name=name,
        icon=icon_path,
    )
    category = crud.create_category(db, category_in)
    if request:
        _normalize_category_icon(request, category)
    return category


@router.put("/{category_id}", response_model=schemas.CategoryResponse)
async def update_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Mettre à jour une catégorie (JSON ou multipart)."""
    content_type = (request.headers.get("content-type") or "").lower()
    data = {}

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        name = form.get("name")
        icon_url = form.get("icon_url") or form.get("icon")
        icon = form.get("icon") or form.get("icon_file") or form.get("file")
        
        # Chercher le fichier dans différents champs possibles
        if isinstance(icon, list):
            icon = icon[0] if icon else None
        if not _is_upload_file(icon):
            for key in ("icon", "icon_file", "file", "icon[]", "icon_path", "iconPath", "iconFile", "files", "upload"):
                for value in form.getlist(key):
                    if _is_upload_file(value):
                        icon = value
                        break
                if _is_upload_file(icon):
                    break
        if not _is_upload_file(icon):
            for _, value in form.multi_items():
                if _is_upload_file(value):
                    icon = value
                    break

        if name is not None and name != "":
            data["name"] = name
        
        # Gérer l'upload de fichier si fourni
        if _is_upload_file(icon):
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            try:
                icon.file.seek(0)
            except Exception:
                pass
            extension = _get_upload_extension(icon)
            filename = f"category_{uuid.uuid4().hex}{extension}"
            file_path = UPLOAD_DIR / filename
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(icon.file, buffer)
            data["icon"] = f"uploads/categories/{filename}"
        elif icon_url is not None and icon_url != "":
            data["icon"] = icon_url
    else:
        # Traitement JSON
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            data.update(body)

    category_in = schemas.CategoryUpdate(**data)
    category = crud.update_category(db, category_id, category_in)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
    _normalize_category_icon(request, category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Supprimer une catégorie."""
    ok = crud.delete_category(db, category_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")


# Routes pour les filtres et fonctionnalités (métadonnées)
router_metadata = APIRouter(prefix="/api", tags=["metadata"])


@router_metadata.get("/filters", response_model=List[schemas.FilterResponse])
def list_filters(db: Session = Depends(get_db)):
    """Récupérer tous les filtres."""
    return crud.get_all_filters(db)


@router_metadata.get("/features", response_model=List[schemas.FeatureResponse])
def list_features(db: Session = Depends(get_db)):
    """Récupérer toutes les fonctionnalités."""
    return crud.get_all_features(db)