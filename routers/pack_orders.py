"""Routeur des commandes pack (user connecté + pack) - champs comme POST /api/orders."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from sqlalchemy.orm import Session
import json

import auth
import crud
import models
import deps
import utils
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/pack-orders", tags=["pack-orders"])


def _normalize_photo_url(request: Request, pack_order: models.PackOrder) -> None:
    utils.normalize_media_attr(pack_order, "photo_url", request, "pack_orders")


@router.get("", response_model=List[schemas.PackOrderWithPackResponse])
def list_pack_orders(
    request: Request,
    pack_id: Optional[int] = None,
    user_id: Optional[int] = None,
    is_done: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Récupérer les commandes pack.
    - Client: uniquement ses propres commandes.
    - Admin: toutes les commandes, optionnel ?user_id= pour filtrer.
    - is_done: filtrer par commande terminée (true/false).
    """
    uid = None if getattr(current_user, "is_admin", False) else current_user.id
    if uid is None and user_id is not None:
        uid = user_id
    orders = crud.get_pack_orders(db, user_id=uid, pack_id=pack_id, is_done=is_done, skip=skip, limit=limit)
    for o in orders:
        _normalize_photo_url(request, o)
    return orders


@router.get("/{pack_order_id}", response_model=schemas.PackOrderWithPackResponse)
def get_pack_order(
    pack_order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Récupérer une commande pack par ID. Client: la sienne. Admin: n'importe laquelle."""
    pack_order = crud.get_pack_order_by_id(db, pack_order_id)
    if not pack_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande pack non trouvée")
    deps.require_access(current_user, pack_order.user_id, "Vous n'avez pas accès à cette commande pack")
    _normalize_photo_url(request, pack_order)
    return pack_order


@router.post("", response_model=schemas.PackOrderWithPackResponse, status_code=status.HTTP_201_CREATED)
async def create_pack_order(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Créer une commande pack.
    Champs requis: customer_name, customer_email, customer_phone, customer_address, items, pack_id.
    Optionnel: notes, description, photo (multipart).
    Accepte JSON ou multipart/form-data.
    """
    content_type = (request.headers.get("content-type") or "").lower()
    data = {}

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        pack_id = form.get("pack_id")
        quantity = form.get("quantity")
        customer_name = form.get("customer_name")
        customer_email = form.get("customer_email")
        customer_phone = form.get("customer_phone")
        customer_address = form.get("customer_address")
        items = form.get("items")
        notes = form.get("notes")
        description = form.get("description")
        photo = utils.find_upload_in_form(form)

        customer_name = utils.form_str(customer_name)
        customer_email = utils.form_str(customer_email)
        customer_phone = utils.form_str(customer_phone)
        customer_address = utils.form_str(customer_address)
        items = utils.form_str(items)
        notes = utils.form_str(notes) or None
        description = utils.form_str(description) or None

        if not customer_name:
            raise HTTPException(status_code=400, detail="Le champ 'customer_name' est requis")
        if not customer_email:
            raise HTTPException(status_code=400, detail="Le champ 'customer_email' est requis")
        if not customer_phone:
            raise HTTPException(status_code=400, detail="Le champ 'customer_phone' est requis")
        if not customer_address:
            raise HTTPException(status_code=400, detail="Le champ 'customer_address' est requis")
        if not items:
            raise HTTPException(status_code=400, detail="Le champ 'items' est requis")
        if not pack_id:
            raise HTTPException(status_code=400, detail="Le champ 'pack_id' est requis")
        if not utils.validate_json_list(items):
            raise HTTPException(
                status_code=400,
                detail="Le champ 'items' doit être un JSON valide. Ex: [{\"title\": \"Design 1\", \"quantity\": 2}]"
            )

        try:
            pack_id = int(pack_id)
            quantity = int(quantity) if quantity else 1
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="pack_id et quantity doivent être des nombres")

        pack = crud.get_pack_by_id(db, pack_id)
        if not pack:
            raise HTTPException(status_code=404, detail="Pack non trouvé")

        photo_url = None
        if utils.is_upload_file(photo):
            try:
                photo_url = utils.save_upload_file(photo, "pack_orders", prefix="pack_order")
            except Exception:
                pass

        pack_order = crud.create_pack_order(
            db,
            schemas.PackOrderCreate(
                pack_id=pack_id,
                quantity=quantity,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_address=customer_address,
                items=items,
                notes=notes,
                description=description,
            ),
            user_id=current_user.id,
            photo_url=photo_url,
        )
    else:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Corps JSON invalide")

        customer_name = str(body.get("customer_name") or "").strip()
        customer_email = str(body.get("customer_email") or "").strip()
        customer_phone = str(body.get("customer_phone") or "").strip()
        customer_address = str(body.get("customer_address") or "").strip()
        items = body.get("items")
        notes = (body.get("notes") or "").strip() or None
        description = (body.get("description") or "").strip() or None
        pack_id = body.get("pack_id")
        quantity = body.get("quantity", 1)

        if not customer_name:
            raise HTTPException(status_code=400, detail="Le champ 'customer_name' est requis")
        if not customer_email:
            raise HTTPException(status_code=400, detail="Le champ 'customer_email' est requis")
        if not customer_phone:
            raise HTTPException(status_code=400, detail="Le champ 'customer_phone' est requis")
        if not customer_address:
            raise HTTPException(status_code=400, detail="Le champ 'customer_address' est requis")
        if items is None:
            raise HTTPException(status_code=400, detail="Le champ 'items' est requis")
        if pack_id is None:
            raise HTTPException(status_code=400, detail="Le champ 'pack_id' est requis")

        if isinstance(items, (dict, list)):
            items = json.dumps(items)
        if not utils.validate_json_list(items):
            raise HTTPException(
                status_code=400,
                detail="Le champ 'items' doit être un JSON valide"
            )

        pack = crud.get_pack_by_id(db, int(pack_id))
        if not pack:
            raise HTTPException(status_code=404, detail="Pack non trouvé")

        pack_order = crud.create_pack_order(
            db,
            schemas.PackOrderCreate(
                pack_id=int(pack_id),
                quantity=int(quantity) if quantity else 1,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_address=customer_address,
                items=items,
                notes=notes,
                description=description,
            ),
            user_id=current_user.id,
        )

    pack_order = crud.get_pack_order_by_id(db, pack_order.id)
    _normalize_photo_url(request, pack_order)
    return pack_order


@router.put("/{pack_order_id}", response_model=schemas.PackOrderWithPackResponse)
def update_pack_order(
    pack_order_id: int,
    body: schemas.PackOrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Modifier une commande pack. Client: la sienne. Admin: n'importe laquelle."""
    pack_order = crud.get_pack_order_by_id(db, pack_order_id)
    if not pack_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande pack non trouvée")
    deps.require_access(current_user, pack_order.user_id, "Vous n'avez pas accès à cette commande pack")
    pack_order = crud.update_pack_order(db, pack_order_id, body)
    pack_order = crud.get_pack_order_by_id(db, pack_order_id)
    _normalize_photo_url(request, pack_order)
    return pack_order


@router.delete("/{pack_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pack_order(
    pack_order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Supprimer une commande pack. Client: la sienne. Admin: n'importe laquelle."""
    pack_order = crud.get_pack_order_by_id(db, pack_order_id)
    if not pack_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande pack non trouvée")
    deps.require_access(current_user, pack_order.user_id, "Vous n'avez pas accès à cette commande pack")
    crud.delete_pack_order(db, pack_order_id)
