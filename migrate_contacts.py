"""Crée la table contacts si elle n'existe pas."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from backend.database import create_all_tables
except ImportError:
    from database import create_all_tables

if __name__ == "__main__":
    print("Création de la table contacts...")
    create_all_tables()
    print("Terminé.")
