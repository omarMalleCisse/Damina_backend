"""Migration pour créer la table payments (PayTech)."""
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent
_root = _backend.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from sqlalchemy import inspect, text
try:
    from backend.database import engine
except ImportError:
    from database import engine


def migrate_payments_table() -> None:
    """Créer la table payments si elle n'existe pas."""
    inspector = inspect(engine)
    dialect = engine.dialect.name
    tables = inspector.get_table_names()
    if "payments" in tables:
        print("[OK] Table payments existe déjà.")
        # Ajouter design_id et user_id si absents (paiement par design)
        cols = [c["name"] for c in inspector.get_columns("payments")]
        with engine.connect() as conn:
            if "design_id" not in cols and dialect == "mysql":
                conn.execute(text("ALTER TABLE payments ADD COLUMN design_id INT NULL"))
                conn.execute(text("ALTER TABLE payments ADD INDEX ix_payments_design_id (design_id)"))
                conn.execute(text("ALTER TABLE payments ADD CONSTRAINT fk_payments_design FOREIGN KEY (design_id) REFERENCES designs(id) ON DELETE SET NULL"))
                conn.commit()
                print("[OK] Colonne design_id ajoutée.")
            elif "design_id" not in cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN design_id INTEGER NULL REFERENCES designs(id) ON DELETE SET NULL"))
                conn.commit()
                print("[OK] Colonne design_id ajoutée.")
            if "user_id" not in cols and dialect == "mysql":
                conn.execute(text("ALTER TABLE payments ADD COLUMN user_id INT NULL"))
                conn.execute(text("ALTER TABLE payments ADD INDEX ix_payments_user_id (user_id)"))
                conn.execute(text("ALTER TABLE payments ADD CONSTRAINT fk_payments_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL"))
                conn.commit()
                print("[OK] Colonne user_id ajoutée.")
            elif "user_id" not in cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL"))
                conn.commit()
                print("[OK] Colonne user_id ajoutée.")
        return
    with engine.connect() as conn:
        if dialect == "mysql":
            conn.execute(text("""
                CREATE TABLE payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NULL,
                    design_id INT NULL,
                    user_id INT NULL,
                    reference_id VARCHAR(255) NOT NULL,
                    amount VARCHAR(50) NOT NULL,
                    currency VARCHAR(10) NOT NULL DEFAULT 'XOF',
                    paytech_id VARCHAR(255) NULL,
                    state VARCHAR(50) NULL,
                    raw_response JSON NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX ix_payments_order_id (order_id),
                    INDEX ix_payments_design_id (design_id),
                    INDEX ix_payments_user_id (user_id),
                    INDEX ix_payments_reference_id (reference_id),
                    INDEX ix_payments_paytech_id (paytech_id),
                    INDEX ix_payments_state (state),
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                    FOREIGN KEY (design_id) REFERENCES designs(id) ON DELETE SET NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """))
        else:
            conn.execute(text("""
                CREATE TABLE payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NULL REFERENCES orders(id) ON DELETE SET NULL,
                    design_id INTEGER NULL REFERENCES designs(id) ON DELETE SET NULL,
                    user_id INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
                    reference_id VARCHAR(255) NOT NULL,
                    amount VARCHAR(50) NOT NULL,
                    currency VARCHAR(10) NOT NULL DEFAULT 'XOF',
                    paytech_id VARCHAR(255) NULL,
                    state VARCHAR(50) NULL,
                    raw_response TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
        conn.commit()
    print("[OK] Table payments créée.")


if __name__ == "__main__":
    print("Migration payments (PayTech)...")
    try:
        migrate_payments_table()
        print("Terminé.")
    except Exception as e:
        print(f"[ERREUR] {e}")
        print("Vérifiez DATABASE_URL / .env et que le serveur MySQL est démarré.")
        sys.exit(1)
