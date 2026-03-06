"""Configuration de la base de données SQLAlchemy."""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# Charger .env en local ; sur Railway les variables viennent de l'environnement
load_dotenv()

_raw_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:Touba123@localhost:3306/broderie_db")
# Railway : MySQL expose MYSQL_URL ou DATABASE_URL ; PostgreSQL utilise postgresql://
if _raw_url.startswith("mysql://") and "pymysql" not in _raw_url:
    _raw_url = _raw_url.replace("mysql://", "mysql+pymysql://", 1)
# Si Railway fournit PostgreSQL, il faut utiliser le driver approprié (psycopg2)
# DATABASE_URL = postgresql+psycopg2://...
DATABASE_URL = _raw_url

engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
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
