"""Normalize design image_path values after moving files to uploads/designs."""
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.orm import Session

import os

from database import SessionLocal
import models


UPLOADS_DIR = Path(__file__).resolve().parent / "uploads" / "designs"


def _load_files() -> dict:
    files = {}
    stems = {}
    if not UPLOADS_DIR.exists():
        return files, stems
    for path in UPLOADS_DIR.iterdir():
        if path.is_file():
            files[path.name.lower()] = path.name
            stems[path.stem.lower()] = path.name
    return files, stems


def _extract_filename(image_path: str) -> str:
    if not image_path:
        return ""
    if "://" in image_path:
        parsed = urlparse(image_path)
        return Path(parsed.path).name
    return Path(image_path).name


def normalize_design_images(db: Session) -> int:
    """Ensure image_path points to uploads/designs/<filename>."""
    files_map, stems_map = _load_files()
    updated = 0
    total_with_image = 0
    missing_in_uploads = 0
    force_webp = os.getenv("FORCE_WEBP", "0") == "1"

    designs = db.query(models.Design).all()
    for design in designs:
        if not design.image_path:
            continue
        total_with_image += 1

        basename = _extract_filename(design.image_path)
        if not basename:
            continue

        filename = files_map.get(basename.lower())
        if not filename:
            stem = Path(basename).stem.lower()
            filename = stems_map.get(stem)
        if not filename:
            if force_webp:
                stem = Path(basename).stem
                filename = f"{stem}.webp"
            else:
                missing_in_uploads += 1
                continue

        normalized = f"uploads/designs/{filename}"
        if design.image_path != normalized:
            design.image_path = normalized
            updated += 1

    if updated:
        db.commit()
    print(
        f"Designs avec image: {total_with_image} | "
        f"Manquants dans uploads: {missing_in_uploads}"
    )
    return updated


if __name__ == "__main__":
    db = SessionLocal()
    try:
        count = normalize_design_images(db)
        print(f"Designs mis a jour: {count}")
    finally:
        db.close()
