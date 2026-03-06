#!/usr/bin/env python3
"""Export the local SQLite DB → frontend/public/data.json for GitHub Pages static deployment.

Usage:
    python export_data.py

Run this whenever you want to update the published snapshot, then commit the result
and push (or run `cd frontend && npm run deploy`).
"""
import json
import os
import sys
from pathlib import Path

# Run from the project root so SQLAlchemy can find appartclaude.db
ROOT = Path(__file__).parent

# Auto-use the project virtualenv if the current interpreter is not already inside it
_venv_python = ROOT / "venv" / "bin" / "python3"
if _venv_python.exists() and Path(sys.executable).resolve() != _venv_python.resolve():
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)

sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Listing

db_path = ROOT / "appartclaude.db"
engine = create_engine(
    "sqlite:///" + str(db_path),
    connect_args={"check_same_thread": False},
)
Session = sessionmaker(bind=engine)


def _dt(v):
    return v.isoformat() if v else None


def serialize(l: Listing) -> dict:
    return {
        "id": l.id,
        "source": l.source,
        "url": l.url,
        "title": l.title,
        "price": l.price,
        "address": l.address,
        "neighborhood": l.neighborhood,
        "bedrooms": l.bedrooms,
        "bathrooms": l.bathrooms,
        "area_sqft": l.area_sqft,
        "has_terrace": bool(l.has_terrace),
        "is_active": bool(l.is_active) if l.is_active is not None else True,
        "latitude": l.latitude,
        "longitude": l.longitude,
        "image_url": l.image_url,
        "description": l.description,
        "first_seen": _dt(l.first_seen),
        "last_seen": _dt(l.last_seen),
    }


data = []

if not db_path.exists():
    print("! database file not found, exporting empty snapshot")
else:
    with Session() as db:
        try:
            listings = (
                db.query(Listing)
                .filter(Listing.is_active != False)  # noqa: E712
                .order_by(Listing.price)
                .all()
            )
            data = [serialize(l) for l in listings]
        except Exception as e:  # sqlite3.OperationalError etc
            print(f"! failed to read listings from database ({e}), exporting empty snapshot")
            data = []

out = ROOT / "frontend" / "public" / "data.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✓ Exported {len(data)} listings → {out}")
