from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
from typing import List, Optional
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import uuid
import json

import crud
import models
import auth
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/orders", tags=["orders"])
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "orders"
_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _build_photo_url(request: Request, photo_path: Optional[str]) -> Optional[str]:
    """Construire l'URL complète de la photo."""
    if not photo_path:
        return None
    if photo_path.startswith("http://") or photo_path.startswith("https://"):
        return photo_path
    file_path = None
    if photo_path.startswith("images/"):
        photo_path = f"uploads/orders/{Path(photo_path).name}"
        file_path = UPLOAD_DIR / Path(photo_path).name
    elif photo_path.startswith("uploads/"):
        file_path = Path(__file__).resolve().parent.parent / photo_path
    elif "/" not in photo_path and "\\" not in photo_path:
        photo_path = f"uploads/orders/{photo_path}"
        file_path = UPLOAD_DIR / Path(photo_path).name

    if file_path and not file_path.exists():
        return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/{photo_path.lstrip('/')}"


def _normalize_order_photo(request: Request, order: models.Order) -> None:
    """Normaliser le chemin de la photo de la commande."""
    if order and getattr(order, "photo_url", None):
        order.photo_url = _build_photo_url(request, order.photo_url)


def _get_upload_extension(photo: UploadFile) -> str:
    """Obtenir l'extension du fichier uploadé."""
    extension = Path(photo.filename or "").suffix
    if extension:
        return extension
    return _CONTENT_TYPE_EXTENSIONS.get(photo.content_type or "", "")


def _is_upload_file(value: object) -> bool:
    """Vérifier si la valeur est un fichier uploadé."""
    return hasattr(value, "file") and hasattr(value, "filename")


def _parse_items_json(items_str: str) -> List[dict]:
    """Parser la chaîne JSON des items."""
    if not items_str:
        return []
    try:
        parsed = json.loads(items_str)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return [parsed]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _validate_items(items_str: str) -> bool:
    """Valider que la chaîne JSON des items est valide."""
    if not items_str:
        return False
    if not isinstance(items_str, str):
        return False
    items_str = items_str.strip()
    if not items_str:
        return False
    try:
        parsed = json.loads(items_str)
        if isinstance(parsed, list):
            # Une liste vide est valide, mais on accepte aussi les listes avec des dicts
            return len(parsed) == 0 or all(isinstance(item, dict) for item in parsed)
        elif isinstance(parsed, dict):
            return True
        return False
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return False


def _parse_bool(value) -> Optional[bool]:
    """Parser une valeur en booléen (form/query)."""
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


@router.get("", response_model=List[schemas.OrderResponse])
def list_orders(
    request: Request,
    status: Optional[str] = None,
    is_done: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """
    Récupérer toutes les commandes.
    - Si authentifié: retourne toutes les commandes ou celles de l'utilisateur selon les permissions
    - Si non authentifié: retourne uniquement les commandes publiques (sans user_id)
    - is_done: filtre par commande terminée (true/false)
    """
    user_id = None
    if current_user:
        # Si admin, peut voir toutes les commandes
        if current_user.is_admin:
            user_id = None
        else:
            # Sinon, seulement ses propres commandes
            user_id = current_user.id
    
    orders = crud.get_orders(db, user_id=user_id, status=status, is_done=is_done, skip=skip, limit=limit)
    for order in orders:
        _normalize_order_photo(request, order)
    return orders


@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """Récupérer une commande par ID."""
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
    
    # Vérifier les permissions
    if current_user:
        if not current_user.is_admin and order.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas accès à cette commande"
            )
    else:
        # Non authentifié: seulement les commandes sans user_id
        if order.user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé"
            )
    
    _normalize_order_photo(request, order)
    return order


@router.post("", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """
    Créer une nouvelle commande.
    Route publique (peut être utilisée sans authentification).
    Accepte JSON ou multipart/form-data.
    Si l'utilisateur est authentifié, la commande sera liée à son compte.
    """
    content_type = (request.headers.get("content-type") or "").lower()
    
    # Déterminer si c'est multipart ou JSON
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        try:
            form = await request.form()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erreur lors du parsing du formulaire: {str(e)}"
            )
        
        customer_name = form.get("customer_name")
        customer_email = form.get("customer_email")
        customer_phone = form.get("customer_phone")
        customer_address = form.get("customer_address")
        items = form.get("items")
        notes = form.get("notes")
        photo = form.get("photo") or form.get("photo_file") or form.get("file")
        
        # Chercher le fichier dans différents champs possibles
        if isinstance(photo, list):
            photo = photo[0] if photo else None
        if not _is_upload_file(photo):
            for key in ("photo", "photo_file", "file", "photo[]", "photo_path", "photoPath", "photoFile", "files", "upload"):
                for value in form.getlist(key):
                    if _is_upload_file(value):
                        photo = value
                        break
                if _is_upload_file(photo):
                    break
        if not _is_upload_file(photo):
            for _, value in form.multi_items():
                if _is_upload_file(value):
                    photo = value
                    break
        
        # Convertir les valeurs en string et valider les champs requis
        # Ignorer les fichiers uploadés dans les champs texte
        try:
            customer_name = str(customer_name).strip() if customer_name and not _is_upload_file(customer_name) else ""
        except (AttributeError, TypeError):
            customer_name = ""
        
        try:
            customer_email = str(customer_email).strip() if customer_email and not _is_upload_file(customer_email) else ""
        except (AttributeError, TypeError):
            customer_email = ""
        
        try:
            customer_phone = str(customer_phone).strip() if customer_phone and not _is_upload_file(customer_phone) else ""
        except (AttributeError, TypeError):
            customer_phone = ""
        
        try:
            customer_address = str(customer_address).strip() if customer_address and not _is_upload_file(customer_address) else ""
        except (AttributeError, TypeError):
            customer_address = ""
        
        try:
            items = str(items).strip() if items and not _is_upload_file(items) else ""
        except (AttributeError, TypeError):
            items = ""
        
        try:
            notes = str(notes).strip() if notes and not _is_upload_file(notes) else None
        except (AttributeError, TypeError):
            notes = None
        
        # Valider les champs requis
        if not customer_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_name' est requis"
            )
        if not customer_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_email' est requis"
            )
        if not customer_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_phone' est requis"
            )
        if not customer_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_address' est requis"
            )
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'items' est requis"
            )
        
        # Valider le format JSON des items
        if not _validate_items(items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'items' doit être une chaîne JSON valide (liste ou objet). Exemple: '[{\"title\": \"Design 1\", \"quantity\": 2}]'"
            )
        
        photo_url = None
        
        # Gérer l'upload de fichier si fourni
        if _is_upload_file(photo):
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            extension = _get_upload_extension(photo)
            filename = f"order_{uuid.uuid4().hex}{extension}"
            file_path = UPLOAD_DIR / filename
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            photo_url = f"uploads/orders/{filename}"
        
        try:
            order_in = schemas.OrderCreate(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_address=customer_address,
                items=items,
                notes=notes,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erreur de validation des données: {str(e)}"
            )
        
        try:
            user_id = current_user.id if current_user else None
            order = crud.create_order(db, order_in, user_id=user_id)
            
            # Ajouter la photo_url si uploadée
            if photo_url:
                order.photo_url = photo_url
                db.add(order)
                db.commit()
                db.refresh(order)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la création de la commande: {str(e)}"
            )
    else:
        # Traitement JSON
        try:
            body = await request.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erreur de parsing JSON: {str(e)}"
            )
        
        if not isinstance(body, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le corps de la requête doit être un objet JSON"
            )
        
        # Valider les champs requis
        customer_name = body.get("customer_name")
        customer_email = body.get("customer_email")
        customer_phone = body.get("customer_phone")
        customer_address = body.get("customer_address")
        items = body.get("items")
        notes = body.get("notes")
        
        if not customer_name or (isinstance(customer_name, str) and customer_name.strip() == ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_name' est requis"
            )
        if not customer_email or (isinstance(customer_email, str) and customer_email.strip() == ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_email' est requis"
            )
        if not customer_phone or (isinstance(customer_phone, str) and customer_phone.strip() == ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_phone' est requis"
            )
        if not customer_address or (isinstance(customer_address, str) and customer_address.strip() == ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'customer_address' est requis"
            )
        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'items' est requis"
            )
        
        # Convertir items en string si c'est un objet/liste
        if isinstance(items, (dict, list)):
            items = json.dumps(items)
        
        # Valider le format JSON des items
        if isinstance(items, str) and not _validate_items(items):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le champ 'items' doit être une chaîne JSON valide (liste ou objet)"
            )
        
        try:
            order_in = schemas.OrderCreate(
                customer_name=str(customer_name).strip(),
                customer_email=str(customer_email).strip(),
                customer_phone=str(customer_phone).strip(),
                customer_address=str(customer_address).strip(),
                items=str(items).strip() if isinstance(items, str) else json.dumps(items),
                notes=str(notes).strip() if notes else None,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Erreur de validation des données: {str(e)}"
            )
        
        try:
            user_id = current_user.id if current_user else None
            order = crud.create_order(db, order_in, user_id=user_id)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la création de la commande: {str(e)}"
            )
    
    _normalize_order_photo(request, order)
    return order


@router.put("/{order_id}", response_model=schemas.OrderResponse)
async def update_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """
    Mettre à jour une commande (JSON ou multipart).
    Nécessite une authentification (admin ou propriétaire de la commande).
    """
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
    
    # Vérifier les permissions
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise"
        )
    
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission de modifier cette commande"
        )
    
    content_type = (request.headers.get("content-type") or "").lower()
    data = {}

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        customer_name = form.get("customer_name")
        customer_email = form.get("customer_email")
        customer_phone = form.get("customer_phone")
        customer_address = form.get("customer_address")
        items = form.get("items")
        notes = form.get("notes")
        status_value = form.get("status")
        is_done_value = form.get("is_done")
        photo_url = form.get("photo_url")
        photo = form.get("photo") or form.get("photo_file") or form.get("file")
        
        # Chercher le fichier dans différents champs possibles
        if isinstance(photo, list):
            photo = photo[0] if photo else None
        if not _is_upload_file(photo):
            for key in ("photo", "photo_file", "file", "photo[]", "photo_path", "photoPath", "photoFile", "files", "upload"):
                for value in form.getlist(key):
                    if _is_upload_file(value):
                        photo = value
                        break
                if _is_upload_file(photo):
                    break
        if not _is_upload_file(photo):
            for _, value in form.multi_items():
                if _is_upload_file(value):
                    photo = value
                    break

        if customer_name is not None and customer_name != "":
            data["customer_name"] = customer_name
        if customer_email is not None and customer_email != "":
            data["customer_email"] = customer_email
        if customer_phone is not None and customer_phone != "":
            data["customer_phone"] = customer_phone
        if customer_address is not None and customer_address != "":
            data["customer_address"] = customer_address
        if items is not None and items != "":
            if not _validate_items(items):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le champ 'items' doit être une chaîne JSON valide"
                )
            data["items"] = items
        if notes is not None:
            data["notes"] = notes
        if status_value is not None and status_value != "":
            data["status"] = status_value
        done = _parse_bool(is_done_value)
        if done is not None:
            data["is_done"] = done

        # Gérer l'upload de fichier si fourni
        if _is_upload_file(photo):
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            try:
                photo.file.seek(0)
            except Exception:
                pass
            extension = _get_upload_extension(photo)
            filename = f"order_{uuid.uuid4().hex}{extension}"
            file_path = UPLOAD_DIR / filename
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
            data["photo_url"] = f"uploads/orders/{filename}"
        elif photo_url is not None and photo_url != "":
            data["photo_url"] = photo_url
    else:
        # Traitement JSON
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            # Valider items si présent
            if "items" in body and isinstance(body["items"], str):
                if not _validate_items(body["items"]):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Le champ 'items' doit être une chaîne JSON valide"
                    )
            data.update(body)

    if data:
        order_in = schemas.OrderUpdate(**data)
        order = crud.update_order(db, order_id, order_in)
    else:
        order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
    _normalize_order_photo(request, order)
    return order


@router.patch("/{order_id}/done", response_model=schemas.OrderResponse)
def set_order_done(
    order_id: int,
    request: Request,
    is_done: bool = True,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """
    Marquer une commande comme terminée ou non (bouton is_done).
    GET ?is_done=true pour marquer terminée, ?is_done=false pour marquer non terminée.
    Nécessite authentification (admin ou propriétaire).
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise"
        )
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission de modifier cette commande"
        )
    order = crud.set_order_done(db, order_id, is_done=is_done)
    _normalize_order_photo(request, order)
    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """
    Supprimer une commande.
    Nécessite une authentification (admin uniquement).
    """
    if not current_user or not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les administrateurs peuvent supprimer des commandes"
        )
    
    ok = crud.delete_order(db, order_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande non trouvée")
