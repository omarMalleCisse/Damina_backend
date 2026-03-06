from typing import List, Optional, Any
from datetime import datetime
import json
from pydantic import BaseModel, field_validator, model_validator, validator


class UserCreate(BaseModel):
    username: str
    email: str
    phone: str
    address: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: str
    address: str
    created_at: datetime
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class FeatureCreate(BaseModel):
    title: str
    description: Optional[str] = None


class FeatureUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class FeatureResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FilterResponse(BaseModel):
    id: str
    label: str

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str
    icon: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    icon: Optional[str] = None

    class Config:
        from_attributes = True


class DesignBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: Optional[str] = None
    is_premium: Optional[bool] = False
    image_path: Optional[str] = None
    images: Optional[List[str]] = None  # plusieurs images — liste de chemins
    category_ids: Optional[List[int]] = None
    download_files: Optional[List[str]] = None  # chemins des fichiers broderie (DST, JEF, PES...)
    longueur: Optional[int] = None  # Longueur du design
    largeur: Optional[int] = None  # Largeur du design
    color: Optional[int] = None  # Nombre de couleurs du design


class DesignCreate(DesignBase):
    pass


class DesignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    is_premium: Optional[bool] = None
    image_path: Optional[str] = None
    images: Optional[List[str]] = None
    category_ids: Optional[List[int]] = None
    download_files: Optional[List[str]] = None
    longueur: Optional[int] = None
    largeur: Optional[int] = None
    color: Optional[int] = None


class DesignResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: Optional[str]
    is_premium: bool
    download_count: int
    downloads: Optional[str]
    image_path: Optional[str]
    images: Optional[List[str]] = None
    download_files: Optional[List[str]] = None
    longueur: Optional[int] = None
    largeur: Optional[int] = None
    color: Optional[int] = None
    categories: List[CategoryResponse] = []

    class Config:
        from_attributes = True


class PaginatedDesignsResponse(BaseModel):
    """Réponse paginée des designs."""
    items: List[DesignResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class CartItemCreate(BaseModel):
    design_id: int
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int


class CartItemResponse(BaseModel):
    id: int
    quantity: int
    design: DesignResponse

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    items: List[CartItemResponse] = []
    total_quantity: int
    total_items: int

    class Config:
        from_attributes = True


class DownloadResponse(BaseModel):
    id: int
    design_id: int
    user_id: Optional[int] = None
    downloaded_at: datetime

    class Config:
        from_attributes = True


class DownloadAdminItem(BaseModel):
    """Un téléchargement avec infos jointes (User, Design) pour l'admin."""
    id: int
    user_id: Optional[int] = None
    design_id: Optional[int] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    design_title: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DownloadListResponse(BaseModel):
    """Réponse paginée pour GET /api/downloads (admin)."""
    downloads: List[DownloadAdminItem]


class PackBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    delivery: Optional[str] = None
    price: Optional[str] = None
    cta_label: Optional[str] = None
    cta_to: Optional[str] = None
    badges: Optional[List[str]] = None


class PackCreate(PackBase):
    pass


class PackUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    delivery: Optional[str] = None
    price: Optional[str] = None
    cta_label: Optional[str] = None
    cta_to: Optional[str] = None
    badges: Optional[List[str]] = None


class PackResponse(PackBase):
    id: int

    class Config:
        from_attributes = True


class PackOrderCreate(BaseModel):
    pack_id: int
    quantity: int = 1
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: str
    items: str  # JSON string ex: [{"title": "Design 1", "quantity": 2}]
    notes: Optional[str] = None
    description: Optional[str] = None


class PackOrderUpdate(BaseModel):
    quantity: Optional[int] = None
    status: Optional[str] = None
    is_done: Optional[bool] = None
    notes: Optional[str] = None
    description: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    items: Optional[str] = None


class PackOrderResponse(BaseModel):
    id: int
    user_id: int
    pack_id: int
    quantity: int
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: str
    items: str
    notes: Optional[str] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    status: str
    is_done: bool
    created_at: datetime
    updated_at: datetime

    @validator("items", pre=True)
    def items_to_str(cls, v: Any) -> str:
        if isinstance(v, (list, dict)):
            return json.dumps(v)
        return str(v) if v is not None else "[]"

    class Config:
        from_attributes = True


class PackOrderWithPackResponse(PackOrderResponse):
    """Commande pack avec les détails du pack et de l'utilisateur."""
    pack: Optional[PackResponse] = None
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class OrderItem(BaseModel):
    """Item individuel dans une commande."""
    design_id: Optional[int] = None
    title: str
    quantity: int = 1
    price: Optional[str] = None
    photo: Optional[str] = None  # URL de la photo de l'item


class OrderBase(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: str
    items: str  # Chaîne JSON à parser
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    items: Optional[str] = None
    photo_url: Optional[str] = None
    status: Optional[str] = None
    is_done: Optional[bool] = None
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: str
    items: str  # Chaîne JSON
    photo_url: Optional[str] = None
    status: str
    is_done: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- PayTech Payments ---


class PaymentCreateRequest(BaseModel):
    """Corps pour initier un paiement : commande (order_id) ou design (design_id)."""
    order_id: Optional[int] = None
    design_id: Optional[int] = None
    amount: float  # Montant à charger (min 100 FCFA)
    currency: str = "XOF"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    target_payment: Optional[str] = None  # Ex: "Orange Money", "Wave"

    @field_validator("amount")
    @classmethod
    def amount_min(cls, v):
        if v is not None and (not isinstance(v, (int, float)) or float(v) < 100):
            raise ValueError("Le montant doit être au moins 100")
        return v

    @model_validator(mode="after")
    def order_or_design(self):
        oid, did = self.order_id, self.design_id
        if (oid is None and did is None) or (oid is not None and did is not None):
            raise ValueError("Préciser soit order_id soit design_id, pas les deux ni aucun")
        return self


class PaymentCreateResponse(BaseModel):
    """Réponse après création d'un paiement : redirection vers PayTech."""
    payment_id: int
    paytech_id: Optional[str] = None
    redirect_url: Optional[str] = None
    reference_id: str
    amount: str
    currency: str
    state: str


class PaymentStatusResponse(BaseModel):
    """Statut d'un paiement."""
    id: int
    order_id: Optional[int] = None
    design_id: Optional[int] = None
    user_id: Optional[int] = None
    reference_id: str
    amount: str
    currency: str
    paytech_id: Optional[str] = None
    state: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Contact ---
class ContactCreate(BaseModel):
    """Envoi d'un message depuis le formulaire de contact."""
    name: str
    email: str
    phone: Optional[str] = None
    subject: str
    message: str


class ContactResponse(BaseModel):
    """Un message contact (pour admin ou confirmation)."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
