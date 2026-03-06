"""
Routeur PayTech - basé sur doc.intech.sn et Postman PayTech x DOC.
Création paiement, webhook IPN (sale_complete), statut.
"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

import auth
import config
import crud
import models
import paytech
from app import schemas
from database import get_db


router = APIRouter(prefix="/api/payments", tags=["payments"])


def _get_webhook_url(request: Request) -> str:
    """URL du webhook - PayTech exige HTTPS. Utiliser PAYTECH_IPN_URL (ngrok) en local."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/payments/webhook"


@router.post("/create", response_model=schemas.PaymentCreateResponse)
def create_payment(
    body: schemas.PaymentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Crée un paiement PayTech : pour une commande (order_id) ou pour un design (design_id).
    Vente par design : envoyer design_id + amount → après paiement redirection vers /designs/{id}/download.
    """
    if not config.PAYTECH_API_KEY or not config.PAYTECH_SIGNING_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Paiement non configuré (PAYTECH_API_KEY / PAYTECH_SIGNING_KEY manquants)",
        )
    # order_id/design_id et amount validés par PaymentCreateRequest (schéma)

    webhook_url = _get_webhook_url(request)
    ipn_url = (getattr(config, "PAYTECH_IPN_URL", None) or "").strip()
    ipn_url = ipn_url or (webhook_url if webhook_url.startswith("https://") else "")
    base_redirect = ipn_url.replace("/api/payments/webhook", "").rstrip("/") if ipn_url else ""
    if not base_redirect or not base_redirect.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PAYTECH_IPN_URL (https) requis. Configurez ngrok dans .env",
        )

    # ref_command doit être unique à chaque tentative (PayTech renvoie 409 sinon)
    unique_suffix = str(int(time.time() * 1000))

    if body.design_id is not None:
        design = crud.get_design_by_id(db, body.design_id)
        if not design:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design introuvable")
        reference_id = f"design-{body.design_id}-{unique_suffix}"
        description = (design.title or f"Design #{body.design_id}")[:255]
        success_url = f"{base_redirect}/payment/success?design_id={body.design_id}"
        cancel_url = f"{base_redirect}/payment/cancel?design_id={body.design_id}"
        custom_field = json.dumps({"design_id": body.design_id, "user_id": current_user.id, "reference": reference_id})
        order_id = None
        design_id = body.design_id
        user_id = current_user.id
    else:
        order = crud.get_order_by_id(db, body.order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commande introuvable")
        if not current_user.is_admin and order.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé à cette commande")
        reference_id = f"order-{body.order_id}-{unique_suffix}"
        description = f"Paiement commande #{body.order_id}"
        success_url = f"{base_redirect}/payment/success?order_id={body.order_id}"
        cancel_url = f"{base_redirect}/payment/cancel?order_id={body.order_id}"
        custom_field = json.dumps({"order_id": body.order_id, "reference": reference_id})
        order_id = body.order_id
        design_id = None
        user_id = None

    try:
        result = paytech.create_payment(
            amount=body.amount,
            currency=body.currency,
            reference_id=reference_id,
            description=description,
            webhook_url=ipn_url,
            success_url=success_url,
            cancel_url=cancel_url,
            target_payment=body.target_payment,
            custom_field=custom_field,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erreur PayTech: {str(e)}. Vérifiez PAYTECH_API_KEY, PAYTECH_SIGNING_KEY et PAYTECH_IPN_URL.",
        )

    paytech_id = result.get("token")
    redirect_url = result.get("redirectUrl") or result.get("redirect_url")

    try:
        payment = crud.create_payment_record(
            db,
            reference_id=reference_id,
            amount=str(body.amount),
            currency=body.currency,
            order_id=order_id,
            design_id=design_id,
            user_id=user_id,
            paytech_id=paytech_id,
            state="PENDING",
            raw_response=result,
        )
    except Exception as e:
        if "design_id" in str(e) or "user_id" in str(e) or "Unknown column" in str(e):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Table payments à jour : exécutez la migration (depuis la racine du projet) : python backend/migrate_payments.py",
            )
        raise

    return schemas.PaymentCreateResponse(
        payment_id=payment.id,
        paytech_id=paytech_id,
        redirect_url=redirect_url,
        reference_id=reference_id,
        amount=str(body.amount),
        currency=body.currency,
        state=payment.state,
    )


@router.post("/webhook")
async def paytech_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook IPN PayTech (sale_complete).
    PayTech envoie type_event, token, ref_command, api_key_sha256, api_secret_sha256.
    Vérification par SHA256 des clés.
    """
    body = await request.body()
    payload = paytech.parse_webhook_payload(body)
    if not payload:
        return JSONResponse(status_code=400, content={"detail": "Invalid JSON"})

    if not paytech.verify_webhook_signature(payload):
        return JSONResponse(status_code=401, content={"detail": "Invalid webhook signature"})

    type_event = payload.get("type_event")
    if type_event != "sale_complete":
        return JSONResponse(status_code=200, content={"status": "ignored", "type_event": type_event})

    ref_command = payload.get("ref_command")
    token = payload.get("token")
    payment = None
    if ref_command:
        payment = crud.get_payment_by_reference(db, ref_command)
    if not payment and token:
        payment = crud.get_payment_by_paytech_id(db, token)

    if payment:
        if payment.state != "COMPLETED":
            crud.update_payment_by_paytech_id(
                db, payment.paytech_id or token, state="COMPLETED", raw_response=payload
            )
            if payment.order_id:
                order = crud.get_order_by_id(db, payment.order_id)
                if order and order.status != "Payée":
                    crud.update_order(db, payment.order_id, schemas.OrderUpdate(status="Payée"))

    return JSONResponse(status_code=200, content={"status": "ok"})


@router.get("/{payment_id}", response_model=schemas.PaymentStatusResponse)
def get_payment_status(
    payment_id: int = Path(..., gt=0, description="ID du paiement"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Récupère le statut d'un paiement (par ID interne)."""
    payment = crud.get_payment_by_id(db, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paiement introuvable")
    if not current_user.is_admin:
        if payment.order_id:
            order = crud.get_order_by_id(db, payment.order_id)
            if order and order.user_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
        elif payment.design_id and payment.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
    return payment
