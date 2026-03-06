"""
API des téléchargements.
- GET /api/downloads : liste des téléchargements (admin uniquement), avec pagination et infos jointes (user, design).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

import auth
import crud
import models
from app import schemas
from database import get_db


router = APIRouter(
    prefix="/api/downloads",
    tags=["downloads"],
)


def _download_to_admin_item(d: models.Download) -> schemas.DownloadAdminItem:
    """Construit un DownloadAdminItem à partir d'un Download avec user/design chargés."""
    user = getattr(d, "user", None)
    design = getattr(d, "design", None)
    return schemas.DownloadAdminItem(
        id=d.id,
        user_id=d.user_id,
        design_id=d.design_id,
        user_name=user.username if user else None,
        user_email=user.email if user else None,
        design_title=design.title if design else None,
        created_at=d.downloaded_at,
    )


@router.get("", response_model=schemas.DownloadListResponse)
def list_downloads_admin(
    skip: int = Query(0, ge=0, description="Nombre d'entrées à sauter"),
    limit: int = Query(200, ge=1, le=500, description="Nombre max d'entrées (1-500)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
):
    """
    Liste l'historique des téléchargements (admin uniquement).
    Pagination : skip, limit (défaut limit=200, max 500).
    Retourne pour chaque entrée : id, user_id, design_id, user_name, user_email, design_title, created_at.
    """
    rows = crud.get_downloads_admin(db, skip=skip, limit=limit)
    items = [_download_to_admin_item(d) for d in rows]
    return schemas.DownloadListResponse(downloads=items)
