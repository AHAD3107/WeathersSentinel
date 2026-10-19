from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.location import Location

router = APIRouter(
    prefix="/api/v1/locations",
    tags=["Locations"],
)


@router.get("/")
def list_locations(db: Session = Depends(get_db)):
    """List all registered weather station locations."""
    locations = db.query(Location).order_by(Location.name.asc()).all()
    return [
        {
            "id": str(loc.id),
            "name": loc.name,
            "district": loc.district,
            "state": loc.state,
            "country": loc.country,
            "latitude": float(loc.latitude) if loc.latitude is not None else None,
            "longitude": float(loc.longitude) if loc.longitude is not None else None,
        }
        for loc in locations
    ]
