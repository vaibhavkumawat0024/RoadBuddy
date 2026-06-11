from fastapi import APIRouter, HTTPException, Depends
from app.schemas.schemas import JournalEntryCreate, JournalOut
from app.core.auth import get_current_user

router = APIRouter()

# In-memory journal store (replace with MongoDB in production)
_journals: dict = {}   # trip_id -> journal
_entries: dict  = {}   # trip_id -> list of entries


# ── Journal ───────────────────────────────────────────────────────────────────

@router.post("/entry", status_code=201)
def add_entry(data: JournalEntryCreate, current_user: dict = Depends(get_current_user)):
    """
    Add a stop to the trip journal.
    Call this when the traveler arrives at each stop.
    Optionally include expense amount, photos (URL), and GPS coordinates.
    """
    trip_id = data.trip_id

    if trip_id not in _entries:
        _entries[trip_id] = []
        _journals[trip_id] = {
            "id": f"j_{trip_id}",
            "trip_id": trip_id,
            "user_id": current_user["user_id"],
            "total_expense_inr": 0.0,
            "is_public": False,
        }

    entry_id = f"e_{trip_id}_{len(_entries[trip_id]) + 1}"
    entry = {
        "id": entry_id,
        "stop_name": data.stop_name,
        "notes": data.notes,
        "expense_inr": data.expense_inr or 0.0,
        "lat": data.lat,
        "lng": data.lng,
        "photos": [],   # In production: accept photo URLs from S3 / Cloudinary
    }
    _entries[trip_id].append(entry)
    _journals[trip_id]["total_expense_inr"] += entry["expense_inr"]

    return {"message": "Journal entry added!", "entry": entry}


@router.get("/{trip_id}", response_model=JournalOut)
def get_journal(trip_id: str, current_user: dict = Depends(get_current_user)):
    """Get the full journal for a trip, including all entries and total expense."""
    journal = _journals.get(trip_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    if journal["user_id"] != current_user["user_id"] and not journal["is_public"]:
        raise HTTPException(status_code=403, detail="This journal is private")

    return JournalOut(
        id=journal["id"],
        trip_id=trip_id,
        entries=_entries.get(trip_id, []),
        total_expense_inr=journal["total_expense_inr"],
        is_public=journal["is_public"],
    )


@router.patch("/{trip_id}/publish")
def publish_journal(trip_id: str, current_user: dict = Depends(get_current_user)):
    """Make a trip journal public so the community can see it."""
    journal = _journals.get(trip_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    if journal["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Not your journal")

    _journals[trip_id]["is_public"] = True
    return {"message": "Journal is now public!", "trip_id": trip_id}


@router.get("/{trip_id}/summary")
def expense_summary(trip_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get a breakdown of expenses by category.
    In production: categorise entries by stop type (food/hotel/fuel/activity).
    """
    journal = _journals.get(trip_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    entries = _entries.get(trip_id, [])
    total   = sum(e["expense_inr"] for e in entries)

    return {
        "trip_id": trip_id,
        "total_expense_inr": round(total, 2),
        "num_stops": len(entries),
        "stops": [{"name": e["stop_name"], "expense_inr": e["expense_inr"]} for e in entries],
    }
