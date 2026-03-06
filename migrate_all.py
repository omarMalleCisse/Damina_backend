"""Script de migration pour creer toutes les tables manquantes."""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import create_all_tables, engine
from backend import models


def migrate_all_tables():
    """Creer toutes les tables definies dans les modeles."""
    print("Demarrage de la migration de toutes les tables...")
    print("Creation des tables: users, carts, cart_items, categories, designs, design_categories,")
    print("  filters, features, packs, downloads, orders...")
    
    try:
        # Utiliser create_all_tables qui importe déjà les modèles
        create_all_tables()
        print("[OK] Toutes les tables ont ete creees ou sont deja a jour.")
        print("[OK] Migration terminee avec succes.")
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate_all_tables()
