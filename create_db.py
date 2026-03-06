"""Utility to (re)create DB tables."""
from backend.database import create_all_tables

if __name__ == "__main__":
    create_all_tables()
    print("Tables créées.")
