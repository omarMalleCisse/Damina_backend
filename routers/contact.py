"""
API Contact : envoi de messages depuis le formulaire de contact.
- POST /api/contact : envoi (public)
- GET /api/contact : liste des messages (admin)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

import auth
import crud
import models
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post("", response_model=schemas.ContactResponse, status_code=status.HTTP_201_CREATED)
def send_contact_message(
    body: schemas.ContactCreate,
    db: Session = Depends(get_db),
):
    """
    Envoi d'un message depuis le formulaire de contact (public, pas d'auth).
    Les messages sont enregistrés en base dans la table contacts.
    """
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le nom est requis.")
    if not body.email or not body.email.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="L'email est requis.")
    if not body.subject or not body.subject.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le sujet est requis.")
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le message est requis.")
    contact = crud.create_contact(db, body)
    return contact


@router.get("", response_model=List[schemas.ContactResponse])
def list_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_admin_user),
):
    """Liste les messages de contact (admin uniquement)."""
    return crud.get_contacts(db, skip=skip, limit=limit, unread_only=unread_only)
