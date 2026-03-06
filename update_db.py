"""Mise à jour de la base pour ajouter phone/address aux users."""
from sqlalchemy import inspect, text

from database import engine, create_all_tables


def update_users_table() -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "users" not in tables:
        create_all_tables()
        print("Table users créée.")
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    alterations = []

    if "phone" not in columns:
        alterations.append("ADD COLUMN phone VARCHAR(30) NOT NULL DEFAULT ''")
    if "address" not in columns:
        alterations.append("ADD COLUMN address VARCHAR(255) NOT NULL DEFAULT ''")

    if alterations:
        sql = "ALTER TABLE users " + ", ".join(alterations)
        with engine.begin() as conn:
            conn.execute(text(sql))
        print("Mise à jour users:", ", ".join(alterations))
    else:
        print("Aucune mise à jour nécessaire pour users.")


if __name__ == "__main__":
    update_users_table()
