"""Migration pour créer la table orders."""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text
from backend.database import engine, create_all_tables


def migrate_orders_table() -> None:
    """Créer la table orders si elle n'existe pas."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "orders" not in tables:
        print("Creation de la table orders...")
        # Importer les modèles pour s'assurer que Order est enregistré
        from backend import models
        models.Base.metadata.create_all(bind=engine, tables=[models.Order.__table__])
        print("[OK] Table orders creee avec succes.")
        return

    # Vérifier les colonnes existantes
    columns = {col["name"] for col in inspector.get_columns("orders")}
    expected_columns = {
        "id", "user_id", "customer_name", "customer_email", "customer_phone",
        "customer_address", "items", "photo_url", "status", "is_done", "notes",
        "created_at", "updated_at"
    }
    
    missing_columns = expected_columns - columns
    
    if missing_columns:
        print(f"Colonnes manquantes detectees: {missing_columns}")
        # MySQL utilise TINYINT(1) pour BOOLEAN, SQLite accepte BOOLEAN
        dialect = engine.dialect.name
        if "is_done" in missing_columns:
            if dialect == "mysql":
                sql = text("ALTER TABLE orders ADD COLUMN is_done TINYINT(1) NOT NULL DEFAULT 0")
            else:
                sql = text("ALTER TABLE orders ADD COLUMN is_done BOOLEAN NOT NULL DEFAULT 0")
            with engine.connect() as conn:
                conn.execute(sql)
                conn.commit()
            print("  [OK] Colonne is_done ajoutee.")
        others = missing_columns - {"is_done"}
        if others:
            print(f"  Autres colonnes manquantes: {others}. Lancez create_all_tables si besoin.")
        print("[OK] Migration terminee.")
    else:
        print("[OK] Table orders existe deja avec toutes les colonnes necessaires.")


if __name__ == "__main__":
    print("Démarrage de la migration pour la table orders...")
    migrate_orders_table()
    print("Migration terminée.")
