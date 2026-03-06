"""
Service PayTech - basé exclusivement sur la documentation officielle :
- https://doc.intech.sn/doc_paytech.php
- https://doc.intech.sn/PayTech%20x%20DOC.postman_collection.json

URL base: https://paytech.sn/api
Authentification: headers API_KEY et API_SECRET
Paramètres: success_url, cancel_url (URLs absolues https selon Postman)
"""
import hashlib
import json
from typing import Any, Dict, Optional

import httpx

import config

PAYTECH_BASE = "https://paytech.sn/api"


def _headers() -> Dict[str, str]:
    """Headers requis par la doc : API_KEY, API_SECRET, Content-Type application/json."""
    return {
        "API_KEY": config.PAYTECH_API_KEY,
        "API_SECRET": config.PAYTECH_SIGNING_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def create_payment(
    amount: float,
    currency: str,
    reference_id: str,
    description: str,
    webhook_url: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
    target_payment: Optional[str] = None,
    custom_field: Optional[str] = None,
    refund_notif_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crée une demande de paiement via POST /payment/request-payment.
    Retourne { success: 1, token, redirect_url, redirectUrl } en cas de succès.
    """
    env = "test" if getattr(config, "PAYTECH_SANDBOX", True) else "prod"
    curr = (currency or "XOF").upper()
    ref = (reference_id or "").strip()
    if not ref:
        raise ValueError("reference_id (ref_command) obligatoire et non vide")
    reference_id = ref[:255]  # limite raisonnable
    ipn_url = (getattr(config, "PAYTECH_IPN_URL", None) or "").strip() or webhook_url

    # PayTech exige ipn_url obligatoire en HTTPS. En local : ngrok + PAYTECH_IPN_URL
    if not ipn_url or not ipn_url.startswith("https://"):
        raise ValueError(
            "PayTech exige ipn_url en HTTPS. En local : lancer 'ngrok http 8000' puis dans .env : "
            "PAYTECH_IPN_URL=https://VOTRE-ID.ngrok-free.app/api/payments/webhook"
        )

    # PayTech exige success_url et cancel_url comme URLs valides (format Postman)
    def _valid_url(u: Optional[str], default: str) -> str:
        u = (u or "").strip()
        if not u or not (u.startswith("http://") or u.startswith("https://")):
            return default
        return u

    success_url = _valid_url(success_url, "https://paytech.sn/mobile/success")
    cancel_url = _valid_url(cancel_url, "https://paytech.sn/mobile/cancel")

    try:
        price_int = max(100, int(float(amount)))
    except (TypeError, ValueError):
        raise ValueError("amount doit être un nombre (min 100)")
    payload: Dict[str, Any] = {
        "item_name": (description or "Commande")[:255],
        "item_price": price_int,
        "currency": curr,
        "ref_command": reference_id,
        "command_name": (description or reference_id)[:255],
        "env": env,
        "ipn_url": ipn_url,
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    if target_payment:
        payload["target_payment"] = target_payment
    if custom_field:
        payload["custom_field"] = custom_field
    if refund_notif_url:
        payload["refund_notif_url"] = refund_notif_url

    url = f"{PAYTECH_BASE}/payment/request-payment"

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload, headers=_headers())

    try:
        body = response.json()
    except Exception:
        body = {}

    if response.status_code != 200:
        msg = body.get("message") or body.get("error") or body.get("detail") or response.text or response.reason_phrase
        raise RuntimeError(f"PayTech: {msg} (HTTP {response.status_code})")

    success = body.get("success") in (1, True)
    if not success:
        msg = body.get("message") or body.get("error") or "Paiement non créé"
        raise RuntimeError(f"PayTech: {msg}")

    token = body.get("token")
    if token and "redirect_url" not in body:
        body["redirect_url"] = f"https://paytech.sn/payment/checkout/{token}"
        body["redirectUrl"] = body["redirect_url"]

    return body


def get_payment_status(token_payment: str) -> Dict[str, Any]:
    """
    Récupère le statut d'un paiement via GET /payment/get-status.
    Paramètre: token_payment (token retourné par request-payment).
    """
    url = f"{PAYTECH_BASE}/payment/get-status"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            url,
            params={"token_payment": token_payment},
            headers=_headers(),
        )

    try:
        body = response.json()
    except Exception:
        body = {}

    if response.status_code != 200:
        msg = body.get("message") or body.get("error") or response.text or response.reason_phrase
        raise RuntimeError(f"PayTech: {msg} (HTTP {response.status_code})")

    return body


def verify_webhook_signature(payload: Dict[str, Any]) -> bool:
    """
    Vérifie le webhook PayTech via api_key_sha256 et api_secret_sha256.
    Selon la collection Postman, PayTech envoie ces hash dans le body.
    """
    key_hash = payload.get("api_key_sha256")
    secret_hash = payload.get("api_secret_sha256")
    if not key_hash or not secret_hash:
        return False

    expected_key = hashlib.sha256(config.PAYTECH_API_KEY.encode("utf-8")).hexdigest()
    expected_secret = hashlib.sha256(config.PAYTECH_SIGNING_KEY.encode("utf-8")).hexdigest()

    return (
        key_hash.lower() == expected_key.lower() and secret_hash.lower() == expected_secret.lower()
    )


def parse_webhook_payload(body: bytes) -> Optional[Dict[str, Any]]:
    """Parse le JSON du webhook."""
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None
