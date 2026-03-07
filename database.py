"""Configuration de la base de données SQLAlchemy."""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# Charger .env en local ; sur Railway les variables viennent de l'environnement
load_dotenv()

# Railway MySQL : DATABASE_URL > MYSQL_URL > MYSQL_PUBLIC_URL > MYSQL_HOST+port+user+pass (ordre de priorité)
_raw_url = (
    os.getenv("DATABASE_URL")
    or os.getenv("MYSQL_URL")
    or os.getenv("MYSQL_PUBLIC_URL")
)
# Sinon construire l'URL à partir des variables séparées (ex. .env avec Railway)
if not _raw_url or "HOST" in _raw_url or "PORT" in _raw_url:
    _h = os.getenv("MYSQL_HOST") or os.getenv("DB_HOST") or "localhost"
    _p = os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or "3306"
    _u = os.getenv("MYSQL_USER") or os.getenv("DB_USER") or "root"
    _w = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD") or os.getenv("DB_PASSWORD") or ""
    _d = os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME") or "broderie_db"
    _raw_url = f"mysql+pymysql://{_u}:{_w}@{_h}:{_p}/{_d}"
if not _raw_url:
    _raw_url = "mysql+pymysql://root:Touba123@localhost:3306/broderie_db"
# Convertir mysql:// en mysql+pymysql:// pour SQLAlchemy + PyMySQL
if _raw_url.startswith("mysql://") and "pymysql" not in _raw_url:
    _raw_url = _raw_url.replace("mysql://", "mysql+pymysql://", 1)
# Si Railway fournit PostgreSQL, il faut utiliser le driver approprié (psycopg2)
# DATABASE_URL = postgresql+psycopg2://...
DATABASE_URL = _raw_url

# Options de connexion (Railway : timeout, SSL si requis)
_connect_args = {"connect_timeout": 10}
if os.getenv("MYSQL_SSL", "").lower() in ("1", "true", "yes"):
    _connect_args["ssl"] = {"ssl_mode": "REQUIRED"}

engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    try:
        from backend import models
    except ImportError:
        import models
    models.Base.metadata.create_all(bind=engine)


def drop_all_tables():
    try:
        from backend import models
    except ImportError:
        import models
    models.Base.metadata.drop_all(bind=engine)
