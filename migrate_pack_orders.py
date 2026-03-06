"""Migration pour créer/mettre à jour la table pack_orders."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text
from backend.database import engine
from backend import models


def migrate_pack_orders_table() -> None:
    """Créer la table pack_orders ou ajouter les colonnes manquantes."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "pack_orders" not in tables:
        print("Création de la table pack_orders...")
        models.Base.metadata.create_all(bind=engine, tables=[models.PackOrder.__table__])
        print("[OK] Table pack_orders créée avec succès.")
        return

    columns = {col["name"] for col in inspector.get_columns("pack_orders")}
    dialect = engine.dialect.name

    add = []
    if "customer_name" not in columns:
        add.append(("customer_name", "VARCHAR(255) NOT NULL DEFAULT ''"))
    if "customer_email" not in columns:
        add.append(("customer_email", "VARCHAR(255) NOT NULL DEFAULT ''"))
    if "customer_phone" not in columns:
        add.append(("customer_phone", "VARCHAR(30) NOT NULL DEFAULT ''"))
    if "customer_address" not in columns:
        add.append(("customer_address", "VARCHAR(500) NOT NULL DEFAULT ''"))
    if "items" not in columns:
        add.append(("items", "JSON" if dialect == "mysql" else "TEXT NOT NULL DEFAULT '[]'"))
    if "description" not in columns:
        add.append(("description", "TEXT NULL"))
    if "photo_url" not in columns:
        add.append(("photo_url", "VARCHAR(500) NULL"))
    if "is_done" not in columns:
        add.append(("is_done", "TINYINT(1) NOT NULL DEFAULT 0" if dialect == "mysql" else "BOOLEAN NOT NULL DEFAULT 0"))

    with engine.connect() as conn:
        for col_name, col_def in add:
            try:
                conn.execute(text(f"ALTER TABLE pack_orders ADD COLUMN {col_name} {col_def}"))
                if col_name == "items" and dialect == "mysql":
                    conn.execute(text("UPDATE pack_orders SET items = '[]' WHERE items IS NULL"))
                    conn.execute(text("ALTER TABLE pack_orders MODIFY COLUMN items JSON NOT NULL"))
                conn.commit()
                print(f"  [OK] Colonne {col_name} ajoutée.")
            except Exception as e:
                conn.rollback()

    columns = {col["name"] for col in inspector.get_columns("pack_orders")}
    expected = {
        "id", "user_id", "pack_id", "quantity", "customer_name", "customer_email",
        "customer_phone", "customer_address", "items", "notes", "description",
        "photo_url", "status", "is_done", "created_at", "updated_at"
    }
    if expected - columns:
        print(f"[WARNING] Colonnes manquantes: {expected - columns}")
    else:
        print("[OK] Table pack_orders à jour.")


if __name__ == "__main__":
    print("Démarrage de la migration pour la table pack_orders...")
    migrate_pack_orders_table()
    print("Migration terminée.")
