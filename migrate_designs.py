"""Migration pour ajouter les colonnes download_files, images, longueur, largeur et color à la table designs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text
from backend.database import engine
from backend import models


def migrate_designs_table() -> None:
    """Ajouter download_files, images (JSON) et longueur, largeur, color (INTEGER) à designs si absents."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "designs" not in tables:
        print("Table designs absente. Lancez migrate_all.")
        return
    columns = {col["name"] for col in inspector.get_columns("designs")}
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if "download_files" not in columns:
            if dialect == "mysql":
                conn.execute(text("ALTER TABLE designs ADD COLUMN download_files JSON NULL"))
            else:
                conn.execute(text("ALTER TABLE designs ADD COLUMN download_files TEXT NULL"))
            conn.commit()
            print("[OK] Colonne download_files ajoutée à designs.")
        else:
            print("[OK] download_files déjà présent.")
        if "images" not in columns:
            if dialect == "mysql":
                conn.execute(text("ALTER TABLE designs ADD COLUMN images JSON NULL"))
            else:
                conn.execute(text("ALTER TABLE designs ADD COLUMN images TEXT NULL"))
            conn.commit()
            print("[OK] Colonne images ajoutée à designs.")
        else:
            print("[OK] images déjà présent.")
        if "longueur" not in columns:
            conn.execute(text("ALTER TABLE designs ADD COLUMN longueur INT NULL"))
            conn.commit()
            print("[OK] Colonne longueur ajoutée à designs.")
        else:
            print("[OK] longueur déjà présent.")
        if "largeur" not in columns:
            conn.execute(text("ALTER TABLE designs ADD COLUMN largeur INT NULL"))
            conn.commit()
            print("[OK] Colonne largeur ajoutée à designs.")
        else:
            print("[OK] largeur déjà présent.")
        if "color" not in columns:
            conn.execute(text("ALTER TABLE designs ADD COLUMN color INT NULL"))
            conn.commit()
            print("[OK] Colonne color ajoutée à designs.")
        else:
            print("[OK] color déjà présent.")


if __name__ == "__main__":
    print("Migration designs (download_files, images, longueur, largeur, color)...")
    migrate_designs_table()
    print("Terminé.")
