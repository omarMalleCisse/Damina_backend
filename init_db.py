"""Initialisation de la base (backend copy).

Crée les tables puis insère des données d'exemple incluant le champ `downloads`.
"""
from .database import create_all_tables, SessionLocal
from .models import Category, Design, Filter, Feature


def seed():
    db = SessionLocal()
    try:
        # Categories
        categories = [
            {"name": "Floral", "icon": "flower.svg"},
            {"name": "Animals", "icon": "animal.svg"},
            {"name": "Seasonal", "icon": "season.svg"},
        ]
        for c in categories:
            if not db.query(Category).filter_by(name=c["name"]).first():
                db.add(Category(**c))

        # Filters
        filters = [
            {"id": "all", "label": "All"},
            {"id": "free", "label": "Free"},
            {"id": "premium", "label": "Premium"},
            {"id": "popular", "label": "Popular"},
        ]
        for f in filters:
            if not db.query(Filter).filter_by(id=f["id"]).first():
                db.add(Filter(**f))

        # Features
        features = [
            {"title": "High Resolution", "description": "High quality stitches"},
            {"title": "Multi Color", "description": "Supports multiple colors"},
        ]
        for fe in features:
            if not db.query(Feature).filter_by(title=fe["title"]).first():
                db.add(Feature(**fe))

        db.commit()

        # Designs (with downloads string for display and download_count int)
        floral = db.query(Category).filter_by(name="Floral").first()
        animals = db.query(Category).filter_by(name="Animals").first()

        if floral and not db.query(Design).filter_by(title="Rose Embroidery").first():
            d1 = Design(
                title="Rose Embroidery",
                description="Elegant rose pattern",
                price="0",
                is_premium=False,
                download_count=1838,
                downloads="1.8k",
                image_path="images/rose.png",
                categories=[floral],
            )
            db.add(d1)

        if animals and not db.query(Design).filter_by(title="Playful Puppy").first():
            d2 = Design(
                title="Playful Puppy",
                description="Cute puppy pattern",
                price="2.99",
                is_premium=True,
                download_count=2400,
                downloads="2.4k",
                image_path="images/puppy.png",
                categories=[animals],
            )
            db.add(d2)

        db.commit()
    finally:
        db.close()


def init():
    create_all_tables()
    seed()


if __name__ == '__main__':
    init()
    print('DB initialisée et données insérées')