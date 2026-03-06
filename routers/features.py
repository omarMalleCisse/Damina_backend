"""Routeur admin pour la gestion des features (fonctionnalités)."""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

import auth
import crud
import models
import deps
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/admin/features", tags=["admin-features"])


@router.get("", response_model=List[schemas.FeatureResponse])
def list_features(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_admin),
):
    """Récupérer toutes les features (admin)."""
    return crud.get_all_features(db)


@router.get("/{feature_id}", response_model=schemas.FeatureResponse)
def get_feature(
    feature_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_admin),
):
    """Récupérer une feature par ID (admin)."""
    feature = crud.get_feature_by_id(db, feature_id)
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature non trouvée")
    return feature


@router.post("", response_model=schemas.FeatureResponse, status_code=status.HTTP_201_CREATED)
def create_feature(
    body: schemas.FeatureCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_admin),
):
    """Créer une feature (admin)."""
    return crud.create_feature(db, body)


@router.put("/{feature_id}", response_model=schemas.FeatureResponse)
def update_feature(
    feature_id: int,
    body: schemas.FeatureUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_admin),
):
    """Modifier une feature (admin)."""
    feature = crud.update_feature(db, feature_id, body)
    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature non trouvée")
    return feature


@router.delete("/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feature(
    feature_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_admin),
):
    """Supprimer une feature (admin)."""
    ok = crud.delete_feature(db, feature_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature non trouvée")
