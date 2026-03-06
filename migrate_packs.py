"""Migration pour créer la table packs et supprimer la colonne image si présente."""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text
from backend.database import engine
from backend import models


def migrate_packs_table() -> None:
    """Créer la table packs si elle n'existe pas ; supprimer la colonne image si elle existe."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "packs" not in tables:
        print("Création de la table packs...")
        models.Base.metadata.create_all(bind=engine, tables=[models.Pack.__table__])
        print("[OK] Table packs créée avec succès.")
    else:
        # Supprimer la colonne image si elle existe (plus utilisée)
        columns = {col["name"] for col in inspector.get_columns("packs")}
        if "image" in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE packs DROP COLUMN image"))
                conn.commit()
            print("[OK] Colonne image supprimée de la table packs.")
        # Vérifier les colonnes attendues (sans image)
        columns = {col["name"] for col in inspector.get_columns("packs")}
        expected_columns = {
            "id", "title", "subtitle", "delivery", "price",
            "cta_label", "cta_to", "badges", "created_at", "updated_at"
        }
        missing = expected_columns - columns
        if missing:
            print(f"[WARNING] Colonnes manquantes sur packs: {missing}")
        else:
            print("[OK] Table packs à jour.")


if __name__ == "__main__":
    print("Démarrage de la migration pour la table packs...")
    migrate_packs_table()
    print("Migration terminée.")
