"""Configuration de l'application (backend copy)"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger .env depuis la racine du projet (damina) si présent
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")
load_dotenv()  # aussi le répertoire courant

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": _int_env("DB_PORT", 3306),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Touba123"),
    "database": os.getenv("DB_NAME", "broderie_db"),
}

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# CORS : en prod, définir CORS_ORIGINS (séparés par des virgules) ou FRONTEND_URL sera ajouté
_cors_env = (os.getenv("CORS_ORIGINS") or "").strip()
if _cors_env:
    CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://damina-8mwqxw2tp-omarmallecisses-projects.vercel.app",
        "https://damina.vercel.app",
    ]
_frontend_url = (os.getenv("FRONTEND_URL") or "").strip().rstrip("/")
if _frontend_url and _frontend_url not in CORS_ORIGINS:
    CORS_ORIGINS.append(_frontend_url)

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 30)

# PayTech payment gateway
PAYTECH_API_KEY = (os.getenv("PAYTECH_API_KEY") or "").strip()  # Clé API
PAYTECH_SIGNING_KEY = (os.getenv("PAYTECH_SIGNING_KEY") or "").strip()  # Clé secrète
PAYTECH_SANDBOX = os.getenv("PAYTECH_SANDBOX", "true").lower() in ("1", "true", "yes")
# api-key = header Api-Key; bearer = Authorization Bearer
PAYTECH_AUTH_HEADER = (os.getenv("PAYTECH_AUTH_HEADER") or "api-key").lower().strip()
PAYTECH_BASE_URL = "https://engine-sandbox.pay.tech" if PAYTECH_SANDBOX else "https://engine.pay.tech"
# Legacy paytech.sn (Sénégal)
PAYTECH_LEGACY = os.getenv("PAYTECH_LEGACY", "true").lower() in ("1", "true", "yes")
# URL IPN/webhook en https (obligatoire pour paytech.sn) - ex: https://xxx.ngrok-free.app/api/payments/webhook
PAYTECH_IPN_URL = (os.getenv("PAYTECH_IPN_URL") or "").strip()
# URL du frontend pour success_url/cancel_url (PayTech exige des URLs absolues)
FRONTEND_URL = (os.getenv("FRONTEND_URL") or "https://damina-8mwqxw2tp-omarmallecisses-projects.vercel.app").strip().rstrip("/")
