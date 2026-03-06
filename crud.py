from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

# Imports absolus
import auth
import models
from app import schemas


def _designs_query(db: Session, filter: str, category: Optional[str]):
    """Requête de base pour les designs (filtres sans skip/limit)."""
    q = db.query(models.Design)

    # Filtrer par catégorie (id numérique ou nom)
    if category:
        try:
            cat_id = int(category)
            q = q.filter(models.Design.categories.any(models.Category.id == cat_id))
        except ValueError:
            q = q.join(models.Category).filter(models.Category.name == category)

    # Appliquer filtres
    if filter == "free":
        q = q.filter(models.Design.is_premium == False)
    elif filter == "premium":
        q = q.filter(models.Design.is_premium == True)
    elif filter == "popular":
        q = q.order_by(desc(models.Design.download_count))
    else:
        q = q.order_by(desc(models.Design.id))

    return q


def get_designs_count(db: Session, filter: str = "all", category: Optional[str] = None) -> int:
    """Compter le total de designs (mêmes filtres que get_designs)."""
    return _designs_query(db, filter, category).count()


def get_designs(
    db: Session,
    filter: str = "all",
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 12,
) -> List[models.Design]:
    """Return designs with optional filters and category filtering.

    - filter: "all" | "free" | "premium" | "popular"
    - category: category id (int) or name (str)
    """
    q = _designs_query(db, filter, category)
    q = q.offset(skip).limit(limit)
    return q.all()


def get_design_by_id(db: Session, design_id: int) -> Optional[models.Design]:
    return db.query(models.Design).filter(models.Design.id == design_id).first()


def create_design(db: Session, design_in: schemas.DesignCreate) -> models.Design:
    data = design_in.dict(exclude_unset=True)
    category_ids = data.pop("category_ids", None)
    design = models.Design(**data)
    if category_ids:
        cats = db.query(models.Category).filter(models.Category.id.in_(category_ids)).all()
        design.categories = cats
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def update_design(db: Session, design_id: int, design_in: schemas.DesignUpdate) -> Optional[models.Design]:
    design = get_design_by_id(db, design_id)
    if not design:
        return None

    data = design_in.dict(exclude_unset=True)
    category_ids = data.pop("category_ids", None)
    # Ne jamais écraser image_path/images par une valeur vide (garder l'existant)
    if data.get("image_path") in (None, ""):
        data.pop("image_path", None)
    if data.get("images") is not None and (not isinstance(data["images"], list) or len(data["images"]) == 0):
        data.pop("images", None)

    for field, value in data.items():
        setattr(design, field, value)

    if category_ids is not None:
        cats = db.query(models.Category).filter(models.Category.id.in_(category_ids)).all()
        design.categories = cats

    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def get_cart_by_user_id(db: Session, user_id: int) -> Optional[models.Cart]:
    return db.query(models.Cart).filter(models.Cart.user_id == user_id).first()


def get_cart_by_id(db: Session, cart_id: int) -> Optional[models.Cart]:
    return db.query(models.Cart).filter(models.Cart.id == cart_id).first()


def get_or_create_cart(
    db: Session,
    user_id: Optional[int] = None,
    cart_id: Optional[int] = None,
) -> models.Cart:
    cart = None
    if cart_id is not None:
        cart = get_cart_by_id(db, cart_id)
    if cart is None and user_id is not None:
        cart = get_cart_by_user_id(db, user_id)
    if cart:
        return cart
    cart = models.Cart(user_id=user_id)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart


def add_to_cart(
    db: Session,
    design_id: int,
    quantity: int = 1,
    user_id: Optional[int] = None,
    cart_id: Optional[int] = None,
) -> Optional[models.Cart]:
    design = get_design_by_id(db, design_id)
    if not design:
        return None
    cart = get_or_create_cart(db, user_id=user_id, cart_id=cart_id)
    existing = None
    for item in cart.items:
        if item.design_id == design_id:
            existing = item
            break
    if existing:
        existing.quantity = (existing.quantity or 0) + max(quantity, 1)
        db.add(existing)
    else:
        item = models.CartItem(cart_id=cart.id, design_id=design_id, quantity=max(quantity, 1))
        db.add(item)
    db.commit()
    db.refresh(cart)
    return cart


def update_cart_item(
    db: Session,
    item_id: int,
    quantity: int,
    user_id: Optional[int] = None,
    cart_id: Optional[int] = None,
) -> Optional[models.Cart]:
    cart = get_or_create_cart(db, user_id=user_id, cart_id=cart_id)
    item = None
    for cart_item in cart.items:
        if cart_item.id == item_id:
            item = cart_item
            break
    if not item:
        return None
    item.quantity = quantity
    db.add(item)
    db.commit()
    db.refresh(cart)
    return cart


def remove_cart_item(
    db: Session,
    item_id: int,
    user_id: Optional[int] = None,
    cart_id: Optional[int] = None,
) -> Optional[models.Cart]:
    cart = get_or_create_cart(db, user_id=user_id, cart_id=cart_id)
    item = None
    for cart_item in cart.items:
        if cart_item.id == item_id:
            item = cart_item
            break
    if not item:
        return None
    db.delete(item)
    db.commit()
    db.refresh(cart)
    return cart


def clear_cart(
    db: Session,
    user_id: Optional[int] = None,
    cart_id: Optional[int] = None,
) -> models.Cart:
    cart = get_or_create_cart(db, user_id=user_id, cart_id=cart_id)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    db.refresh(cart)
    return cart


def delete_design(db: Session, design_id: int) -> bool:
    design = get_design_by_id(db, design_id)
    if not design:
        return False
    db.delete(design)
    db.commit()
    return True


def increment_download_count(db: Session, design_id: int) -> Optional[models.Design]:
    design = get_design_by_id(db, design_id)
    if not design:
        return None
    design.download_count = (design.download_count or 0) + 1
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


def create_download(
    db: Session,
    design_id: int,
    user_id: Optional[int] = None,
) -> Optional[models.Download]:
    design = get_design_by_id(db, design_id)
    if not design:
        return None
    download = models.Download(design_id=design_id, user_id=user_id)
    db.add(download)
    db.commit()
    db.refresh(download)
    return download


def get_downloads(
    db: Session,
    design_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Download]:
    q = db.query(models.Download)
    if design_id is not None:
        q = q.filter(models.Download.design_id == design_id)
    if user_id is not None:
        q = q.filter(models.Download.user_id == user_id)
    q = q.order_by(models.Download.downloaded_at.desc())
    if skip:
        q = q.offset(skip)
    if limit:
        q = q.limit(limit)
    return q.all()


def get_downloads_admin(
    db: Session,
    skip: int = 0,
    limit: int = 200,
) -> List[models.Download]:
    """Liste des téléchargements avec User et Design chargés (pour l'admin)."""
    q = (
        db.query(models.Download)
        .options(
            joinedload(models.Download.user),
            joinedload(models.Download.design),
        )
        .order_by(models.Download.downloaded_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return q.all()


def get_packs(db: Session) -> List[models.Pack]:
    return db.query(models.Pack).all()


def get_pack_by_id(db: Session, pack_id: int) -> Optional[models.Pack]:
    return db.query(models.Pack).filter(models.Pack.id == pack_id).first()


def create_pack(db: Session, pack_in: schemas.PackCreate) -> models.Pack:
    data = pack_in.dict(exclude_unset=True)
    pack = models.Pack(**data)
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack


def update_pack(db: Session, pack_id: int, pack_in: schemas.PackUpdate) -> Optional[models.Pack]:
    pack = get_pack_by_id(db, pack_id)
    if not pack:
        return None
    data = pack_in.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(pack, field, value)
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack


def delete_pack(db: Session, pack_id: int) -> bool:
    pack = get_pack_by_id(db, pack_id)
    if not pack:
        return False
    db.delete(pack)
    db.commit()
    return True


# ========== PACK_ORDERS (COMMANDES PACK) ==========


def get_pack_orders(
    db: Session,
    user_id: Optional[int] = None,
    pack_id: Optional[int] = None,
    is_done: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.PackOrder]:
    """Récupérer les commandes pack avec détails du pack et user (filtrer par user connecté et/ou pack)."""
    q = db.query(models.PackOrder).options(
        joinedload(models.PackOrder.pack),
        joinedload(models.PackOrder.user),
    )
    if user_id is not None:
        q = q.filter(models.PackOrder.user_id == user_id)
    if pack_id is not None:
        q = q.filter(models.PackOrder.pack_id == pack_id)
    if is_done is not None:
        q = q.filter(models.PackOrder.is_done == is_done)
    q = q.order_by(models.PackOrder.created_at.desc())
    q = q.offset(skip).limit(limit)
    return q.all()


def get_pack_order_by_id(db: Session, pack_order_id: int) -> Optional[models.PackOrder]:
    return (
        db.query(models.PackOrder)
        .options(
            joinedload(models.PackOrder.pack),
            joinedload(models.PackOrder.user),
        )
        .filter(models.PackOrder.id == pack_order_id)
        .first()
    )


def create_pack_order(
    db: Session,
    pack_order_in: schemas.PackOrderCreate,
    user_id: int,
    photo_url: Optional[str] = None,
) -> models.PackOrder:
    """Créer une commande pack pour l'utilisateur connecté."""
    data = pack_order_in.dict(exclude_unset=True)
    data.pop("is_done", None)
    pack_order = models.PackOrder(user_id=user_id, status="En attente", is_done=False, **data)
    if photo_url:
        pack_order.photo_url = photo_url
    db.add(pack_order)
    db.commit()
    db.refresh(pack_order)
    return pack_order


def update_pack_order(
    db: Session, pack_order_id: int, pack_order_in: schemas.PackOrderUpdate
) -> Optional[models.PackOrder]:
    pack_order = get_pack_order_by_id(db, pack_order_id)
    if not pack_order:
        return None
    data = pack_order_in.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(pack_order, field, value)
    db.add(pack_order)
    db.commit()
    db.refresh(pack_order)
    return pack_order


def delete_pack_order(db: Session, pack_order_id: int) -> bool:
    pack_order = get_pack_order_by_id(db, pack_order_id)
    if not pack_order:
        return False
    db.delete(pack_order)
    db.commit()
    return True


def get_all_categories(db: Session) -> List[models.Category]:
    return db.query(models.Category).all()


def get_category_by_id(db: Session, category_id: int) -> Optional[models.Category]:
    return db.query(models.Category).filter(models.Category.id == category_id).first()


def create_category(db: Session, category_in: schemas.CategoryCreate) -> models.Category:
    data = category_in.dict(exclude_unset=True)
    category = models.Category(**data)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, category_in: schemas.CategoryUpdate) -> Optional[models.Category]:
    category = get_category_by_id(db, category_id)
    if not category:
        return None

    data = category_in.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(category, field, value)

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> bool:
    category = get_category_by_id(db, category_id)
    if not category:
        return False
    db.delete(category)
    db.commit()
    return True


def get_all_filters(db: Session) -> List[models.Filter]:
    return db.query(models.Filter).all()


def get_all_features(db: Session) -> List[models.Feature]:
    return db.query(models.Feature).all()


def get_feature_by_id(db: Session, feature_id: int) -> Optional[models.Feature]:
    return db.query(models.Feature).filter(models.Feature.id == feature_id).first()


def create_feature(db: Session, feature_in: schemas.FeatureCreate) -> models.Feature:
    data = feature_in.dict(exclude_unset=True)
    feature = models.Feature(**data)
    db.add(feature)
    db.commit()
    db.refresh(feature)
    return feature


def update_feature(db: Session, feature_id: int, feature_in: schemas.FeatureUpdate) -> Optional[models.Feature]:
    feature = get_feature_by_id(db, feature_id)
    if not feature:
        return None
    data = feature_in.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(feature, field, value)
    db.add(feature)
    db.commit()
    db.refresh(feature)
    return feature


def delete_feature(db: Session, feature_id: int) -> bool:
    feature = get_feature_by_id(db, feature_id)
    if not feature:
        return False
    db.delete(feature)
    db.commit()
    return True


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed_password = auth.get_password_hash(user_in.password)
    user = models.User(
        username=user_in.username,
        email=user_in.email,
        phone=user_in.phone,
        address=user_in.address,
        hashed_password=hashed_password,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()


def update_user(db: Session, user_id: int, user_in: schemas.UserUpdate) -> Optional[models.User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    data = user_in.dict(exclude_unset=True)
    password = data.pop("password", None)
    for field, value in data.items():
        setattr(user, field, value)
    if password:
        user.hashed_password = auth.get_password_hash(password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not auth.verify_password(password, user.hashed_password):
        return None
    return user


# ========== ORDERS (COMMANDES) ==========

def get_orders(
    db: Session,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    is_done: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Order]:
    """Récupérer les commandes avec filtres optionnels."""
    q = db.query(models.Order)
    if user_id is not None:
        q = q.filter(models.Order.user_id == user_id)
    if status is not None:
        q = q.filter(models.Order.status == status)
    if is_done is not None:
        q = q.filter(models.Order.is_done == is_done)
    q = q.order_by(models.Order.created_at.desc())
    if skip:
        q = q.offset(skip)
    if limit:
        q = q.limit(limit)
    return q.all()


def get_order_by_id(db: Session, order_id: int) -> Optional[models.Order]:
    """Récupérer une commande par ID."""
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def create_order(db: Session, order_in: schemas.OrderCreate, user_id: Optional[int] = None) -> models.Order:
    """Créer une nouvelle commande."""
    data = order_in.dict(exclude_unset=True)
    data.pop("is_done", None)  # ne pas permettre de le fixer à la création
    order = models.Order(
        user_id=user_id,
        status="En attente",
        is_done=False,
        **data
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def update_order(db: Session, order_id: int, order_in: schemas.OrderUpdate) -> Optional[models.Order]:
    """Mettre à jour une commande."""
    order = get_order_by_id(db, order_id)
    if not order:
        return None
    
    data = order_in.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(order, field, value)
    
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, order_id: int) -> bool:
    """Supprimer une commande."""
    order = get_order_by_id(db, order_id)
    if not order:
        return False
    db.delete(order)
    db.commit()
    return True


def set_order_done(db: Session, order_id: int, is_done: bool = True) -> Optional[models.Order]:
    """Marquer une commande comme terminée ou non (bouton is_done)."""
    order = get_order_by_id(db, order_id)
    if not order:
        return None
    order.is_done = is_done
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_orders_by_pack_id(
    db: Session,
    pack_id: int,
    pack_title: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.Order]:
    """
    Récupérer les commandes dont les items contiennent ce pack.
    Filtre par pack_id ou par titre de pack (ex: "pack_usb") dans les items.
    """
    import json
    # Récupérer les commandes puis filtrer côté Python (items en JSON)
    all_orders = get_orders(db, skip=0, limit=2000)
    result = []
    for order in all_orders:
        try:
            raw = order.items
            if isinstance(raw, str):
                items = json.loads(raw) if raw else []
            else:
                items = raw or []
            if not isinstance(items, list):
                items = [items] if isinstance(items, dict) else []
        except (TypeError, json.JSONDecodeError):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("pack_id") == pack_id:
                result.append(order)
                break
            if pack_title and str(item.get("title") or "").lower() == str(pack_title).lower():
                result.append(order)
                break
    return result[skip : skip + limit]


# --- Payments (PayTech) ---


def create_payment_record(
    db: Session,
    reference_id: str,
    amount: str,
    currency: str,
    order_id: Optional[int] = None,
    design_id: Optional[int] = None,
    user_id: Optional[int] = None,
    paytech_id: Optional[str] = None,
    state: Optional[str] = None,
    raw_response: Optional[dict] = None,
) -> models.Payment:
    """Enregistre un paiement en base (commande ou design)."""
    payment = models.Payment(
        order_id=order_id,
        design_id=design_id,
        user_id=user_id,
        reference_id=reference_id,
        amount=amount,
        currency=currency,
        paytech_id=paytech_id,
        state=state or "PENDING",
        raw_response=raw_response,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def get_payment_by_id(db: Session, payment_id: int) -> Optional[models.Payment]:
    return db.query(models.Payment).filter(models.Payment.id == payment_id).first()


def get_payment_by_paytech_id(db: Session, paytech_id: str) -> Optional[models.Payment]:
    return db.query(models.Payment).filter(models.Payment.paytech_id == paytech_id).first()


def get_payment_by_reference(db: Session, reference_id: str) -> Optional[models.Payment]:
    return db.query(models.Payment).filter(models.Payment.reference_id == reference_id).first()


def update_payment_state(
    db: Session,
    payment_id: int,
    state: str,
    raw_response: Optional[dict] = None,
) -> Optional[models.Payment]:
    payment = get_payment_by_id(db, payment_id)
    if not payment:
        return None
    payment.state = state
    if raw_response is not None:
        payment.raw_response = raw_response
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def has_user_paid_for_design(
    db: Session, design_id: int, user_id: int
) -> bool:
    """Vérifie si l'utilisateur a un paiement COMPLETED pour ce design."""
    q = (
        db.query(models.Payment)
        .filter(
            models.Payment.design_id == design_id,
            models.Payment.user_id == user_id,
            models.Payment.state == "COMPLETED",
        )
    )
    return q.first() is not None


def update_payment_by_paytech_id(
    db: Session,
    paytech_id: str,
    state: str,
    raw_response: Optional[dict] = None,
) -> Optional[models.Payment]:
    payment = get_payment_by_paytech_id(db, paytech_id)
    if not payment:
        return None
    payment.state = state
    if raw_response is not None:
        payment.raw_response = raw_response
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def create_contact(db: Session, contact_in: schemas.ContactCreate) -> models.Contact:
    """Enregistre un message de contact."""
    contact = models.Contact(
        name=contact_in.name.strip(),
        email=contact_in.email.strip(),
        phone=contact_in.phone.strip() if contact_in.phone else None,
        subject=contact_in.subject.strip(),
        message=contact_in.message.strip(),
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_contacts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    unread_only: bool = False,
) -> List[models.Contact]:
    """Liste les messages contact (admin)."""
    q = db.query(models.Contact)
    if unread_only:
        q = q.filter(models.Contact.is_read == False)
    q = q.order_by(models.Contact.created_at.desc())
    return q.offset(skip).limit(limit).all()