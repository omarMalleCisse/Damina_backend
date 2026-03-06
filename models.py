"""Modèles SQLAlchemy pour l'application de designs de broderie."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table, Index, JSON
)
from sqlalchemy.orm import declarative_base, relationship, Mapped
from typing import List, Optional

Base = declarative_base()

# Association table design <-> category
design_category_association = Table(
    'design_categories',
    Base.metadata,
    Column('design_id', Integer, ForeignKey('designs.id', ondelete='CASCADE'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id', ondelete='CASCADE'), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=False)
    address = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    cart: Mapped["Cart"] = relationship(
        "Cart",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="cart")
    items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
    )

    @property
    def total_quantity(self) -> int:
        return sum((item.quantity or 0) for item in self.items)

    @property
    def total_items(self) -> int:
        return len(self.items)


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    icon = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    designs: Mapped[List["Design"]] = relationship(
        "Design",
        secondary=design_category_association,
        back_populates="categories",
    )


class Design(Base):
    __tablename__ = 'designs'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(String(50), nullable=True)
    is_premium = Column(Boolean, default=False, index=True)
    download_count = Column(Integer, default=0, index=True)
    downloads = Column(String(50), nullable=True)
    image_path = Column(String(500), nullable=True)  # Image principale (compatibilité)
    images = Column(JSON, nullable=True)  # Plusieurs images — liste de chemins
    download_files = Column(JSON, nullable=True)  # Fichiers broderie (DST, JEF, PES...) — liste de chemins
    longueur = Column(Integer, nullable=True)  # Longueur du design (en mm ou pixels)
    largeur = Column(Integer, nullable=True)  # Largeur du design (en mm ou pixels)
    color = Column(Integer, nullable=True)  # Nombre de couleurs du design
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    categories: Mapped[List[Category]] = relationship(
        "Category",
        secondary=design_category_association,
        back_populates="designs",
    )

    cart_items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="design",
        cascade="all, delete-orphan",
    )

    downloads_history: Mapped[List["Download"]] = relationship(
        "Download",
        back_populates="design",
        cascade="all, delete-orphan",
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    design_id = Column(Integer, ForeignKey("designs.id", ondelete="CASCADE"), index=True)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    design: Mapped["Design"] = relationship("Design", back_populates="cart_items")





class Filter(Base):
    __tablename__ = 'filters'
    id = Column(String(50), primary_key=True, index=True)
    label = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Feature(Base):
    __tablename__ = 'features'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Pack(Base):
    __tablename__ = "packs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    subtitle = Column(Text, nullable=True)
    delivery = Column(Text, nullable=True)
    price = Column(String(50), nullable=True)
    cta_label = Column(String(100), nullable=True)
    cta_to = Column(String(255), nullable=True)
    badges = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PackOrder(Base):
    """Commande pack : lien utilisateur connecté + pack (mêmes champs que orders)."""
    __tablename__ = "pack_orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pack_id = Column(Integer, ForeignKey("packs.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)
    customer_phone = Column(String(30), nullable=False)
    customer_address = Column(Text, nullable=False)
    items = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    status = Column(String(50), default="En attente", nullable=False, index=True)
    is_done = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
    pack: Mapped["Pack"] = relationship("Pack")


class Download(Base):
    __tablename__ = "downloads"
    id = Column(Integer, primary_key=True, index=True)
    design_id = Column(Integer, ForeignKey("designs.id", ondelete="CASCADE"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    downloaded_at = Column(DateTime, default=datetime.utcnow, index=True)

    design: Mapped["Design"] = relationship("Design", back_populates="downloads_history")
    user: Mapped[Optional["User"]] = relationship("User")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False, index=True)
    customer_phone = Column(String(30), nullable=False)
    customer_address = Column(Text, nullable=False)
    items = Column(JSON, nullable=False)  # Chaîne JSON à parser
    photo_url = Column(String(500), nullable=True)
    status = Column(String(50), default="En attente", nullable=False, index=True)
    is_done = Column(Boolean, default=False, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship("User")


class Payment(Base):
    """Paiement PayTech : commande (order_id) ou design (design_id + user_id)."""
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    design_id = Column(Integer, ForeignKey("designs.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reference_id = Column(String(255), nullable=False, index=True)
    amount = Column(String(50), nullable=False)
    currency = Column(String(10), nullable=False, default="XOF")
    paytech_id = Column(String(255), nullable=True, index=True)
    state = Column(String(50), nullable=True, index=True)
    raw_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order: Mapped[Optional["Order"]] = relationship("Order")
    design: Mapped[Optional["Design"]] = relationship("Design")
    user: Mapped[Optional["User"]] = relationship("User")


class Contact(Base):
    """Messages du formulaire de contact."""
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
