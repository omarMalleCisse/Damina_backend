from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from typing import List
from sqlalchemy.orm import Session

# Imports absolus
import crud
import models
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=List[schemas.CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """Récupérer toutes les catégories."""
    categories = crud.get_all_categories(db)
    return categories


@router.get("/{category_id}", response_model=schemas.CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Récupérer une catégorie par ID."""
    category = crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
    return category


@router.post("", response_model=schemas.CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(request: Request, db: Session = Depends(get_db)):
    """Créer une nouvelle catégorie (multipart/form-data ou JSON).

    On accepte JSON pour éviter les 422 lors des scripts/migrations.
    """
    content_type = (request.headers.get("content-type") or "").lower()

    name = None
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        name = form.get("name")
    else:
        # JSON: {"name": "..."} (on ignore volontairement d'éventuels champs en plus)
        try:
            body = await request.json()
        except Exception:
            body = None
        if isinstance(body, dict):
            name = body.get("name")

    if name is None or str(name).strip() == "":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Champ 'name' requis")

    category_in = schemas.CategoryCreate(name=str(name).strip())
    return crud.create_category(db, category_in)


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

        if name is not None and name != "":
            data["name"] = name
    else:
        # Traitement JSON
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            name = body.get("name")
            if name is not None and name != "":
                data["name"] = name

    category_in = schemas.CategoryUpdate(**data)
    category = crud.update_category(db, category_id, category_in)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie non trouvée")
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