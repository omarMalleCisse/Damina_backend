from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from typing import List, Optional
from sqlalchemy.orm import Session

import auth
import crud
import models
from app import schemas
from database import get_db
import utils


router = APIRouter(prefix="/api/packs", tags=["packs"])


def _parse_badges(value: Optional[str]) -> Optional[List[str]]:
    return utils.parse_json_list_or_badges(value)


@router.get("", response_model=List[schemas.PackResponse])
def list_packs(request: Request, db: Session = Depends(get_db)):
    """Récupérer tous les packs."""
    return crud.get_packs(db)


@router.get("/{pack_id}", response_model=schemas.PackResponse)
def get_pack(pack_id: int, request: Request, db: Session = Depends(get_db)):
    """Récupérer un pack par ID."""
    pack = crud.get_pack_by_id(db, pack_id)
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack non trouvé")
    return pack


@router.get("/{pack_id}/commandes", response_model=List[schemas.OrderResponse])
def get_pack_commandes(
    pack_id: int,
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Récupérer les commandes liées à ce pack (ex: pack_usb).
    Réservé aux utilisateurs authentifiés (validation des commandes).
    Les items des commandes doivent contenir pack_id ou un titre correspondant au pack.
    """
    pack = crud.get_pack_by_id(db, pack_id)
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack non trouvé")
    import deps
    deps.ensure_admin(current_user)
    orders = crud.get_orders_by_pack_id(
        db, pack_id=pack_id, pack_title=pack.title, skip=skip, limit=limit
    )
    # Normaliser les URLs photo comme dans le routeur orders
    from routers.orders import _normalize_order_photo
    for order in orders:
        _normalize_order_photo(request, order)
    return orders


@router.post("", response_model=schemas.PackResponse, status_code=status.HTTP_201_CREATED)
def create_pack(
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    delivery: Optional[str] = Form(None),
    delivery_info: Optional[str] = Form(None),  # Alias pour delivery
    price: Optional[str] = Form(None),
    cta_label: Optional[str] = Form(None),
    cta_to: Optional[str] = Form(None),
    badges: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Créer un nouveau pack."""
    delivery_value = delivery or delivery_info
    pack_in = schemas.PackCreate(
        title=title,
        subtitle=subtitle,
        delivery=delivery_value,
        price=price,
        cta_label=cta_label,
        cta_to=cta_to,
        badges=_parse_badges(badges),
    )
    return crud.create_pack(db, pack_in)


@router.put("/{pack_id}", response_model=schemas.PackResponse)
async def update_pack(
    pack_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Mettre à jour un pack (JSON ou multipart)."""
    content_type = (request.headers.get("content-type") or "").lower()
    data = {}

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        title = form.get("title")
        subtitle = form.get("subtitle")
        delivery = form.get("delivery") or form.get("delivery_info")
        price = form.get("price")
        cta_label = form.get("cta_label")
        cta_to = form.get("cta_to")
        badges = form.get("badges")

        if title is not None and title != "":
            data["title"] = title
        if subtitle is not None and subtitle != "":
            data["subtitle"] = subtitle
        if delivery is not None and delivery != "":
            data["delivery"] = delivery
        if price is not None and price != "":
            data["price"] = price
        if cta_label is not None and cta_label != "":
            data["cta_label"] = cta_label
        if cta_to is not None and cta_to != "":
            data["cta_to"] = cta_to
        if badges is not None:
            parsed_badges = _parse_badges(badges)
            if parsed_badges is not None:
                data["badges"] = parsed_badges
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            data.update(body)
            if "badges" in data and isinstance(data["badges"], str):
                data["badges"] = _parse_badges(data["badges"])

    pack_in = schemas.PackUpdate(**data)
    pack = crud.update_pack(db, pack_id, pack_in)
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack non trouvé")
    return pack


@router.delete("/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pack(pack_id: int, db: Session = Depends(get_db)):
    """Supprimer un pack."""
    ok = crud.delete_pack(db, pack_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pack non trouvé")
