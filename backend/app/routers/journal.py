from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import JournalEntryCreate, JournalOut
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import Journal, JournalEntry as JournalEntryModel
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ── Journal ───────────────────────────────────────────────────────────────────

@router.post("/entry", status_code=201)
def add_entry(
    data: JournalEntryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a stop to the trip journal."""
    trip_id = data.trip_id
    user_id = int(current_user["user_id"])

    # Get or create journal for this trip
    journal = db.query(Journal).filter(
        Journal.trip_id == trip_id
    ).first()

    if not journal:
        journal = Journal(
            trip_id           = trip_id,
            user_id           = user_id,
            total_expense_inr = 0.0,
            is_public         = False,
        )
        db.add(journal)
        db.commit()
        db.refresh(journal)

    # Add entry
    entry = JournalEntryModel(
        journal_id  = journal.id,
        stop_name   = data.stop_name,
        notes       = data.notes,
        expense_inr = data.expense_inr or 0.0,
        lat         = data.lat,
        lng         = data.lng,
    )
    db.add(entry)

    # Update total expense
    journal.total_expense_inr += entry.expense_inr
    db.commit()
    db.refresh(entry)

    return {
        "message": "Journal entry added!",
        "entry": {
            "id": str(entry.id),
            "stop_name": entry.stop_name,
            "notes": entry.notes,
            "expense_inr": entry.expense_inr,
            "lat": entry.lat,
            "lng": entry.lng,
        }
    }


@router.get("/{trip_id}", response_model=JournalOut)
def get_journal(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the full journal for a trip."""
    journal = db.query(Journal).filter(
        Journal.trip_id == trip_id
    ).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    if journal.user_id != int(current_user["user_id"]) and not journal.is_public:
        raise HTTPException(status_code=403, detail="This journal is private")

    entries = db.query(JournalEntryModel).filter(
        JournalEntryModel.journal_id == journal.id
    ).all()

    return JournalOut(
        id                = str(journal.id),
        trip_id           = trip_id,
        entries           = [
            {
                "id": str(e.id),
                "stop_name": e.stop_name,
                "notes": e.notes,
                "expense_inr": e.expense_inr,
                "lat": e.lat,
                "lng": e.lng,
            }
            for e in entries
        ],
        total_expense_inr = journal.total_expense_inr,
        is_public         = journal.is_public,
    )


@router.patch("/{trip_id}/publish")
def publish_journal(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Make a trip journal public."""
    journal = db.query(Journal).filter(
        Journal.trip_id == trip_id
    ).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    if journal.user_id != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Not your journal")

    journal.is_public = True
    db.commit()

    return {"message": "Journal is now public!", "trip_id": trip_id}


@router.get("/{trip_id}/summary")
def expense_summary(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get expense breakdown for a trip journal."""
    journal = db.query(Journal).filter(
        Journal.trip_id == trip_id
    ).first()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")

    entries = db.query(JournalEntryModel).filter(
        JournalEntryModel.journal_id == journal.id
    ).all()

    total = sum(e.expense_inr for e in entries)

    return {
        "trip_id": trip_id,
        "total_expense_inr": round(total, 2),
        "num_stops": len(entries),
        "stops": [
            {"name": e.stop_name, "expense_inr": e.expense_inr}
            for e in entries
        ],
    }


# ── AI Journal Summarizer ─────────────────────────────────────────────────────

class JournalEntry(BaseModel):
    day: int
    date: Optional[str] = ""
    location: Optional[str] = ""
    mood: Optional[str] = "neutral"
    text: str
    expenses_inr: Optional[float] = 0


class SummarizeRequest(BaseModel):
    origin: str
    destination: str
    entries: list[JournalEntry]
    total_days: int
    total_cost_inr: Optional[float] = 0
    group_type: Optional[str] = "friends"
    num_people: Optional[int] = 2


@router.post("/summarize")
async def summarize_journal(request: SummarizeRequest):
    """AI-powered trip journal summarizer."""
    try:
        from app.services.journal_summarizer import summarize_trip_journal
        entries_dict = [e.dict() for e in request.entries]
        result = await summarize_trip_journal(
            origin=request.origin,
            destination=request.destination,
            entries=entries_dict,
            total_days=request.total_days,
            total_cost_inr=request.total_cost_inr,
            group_type=request.group_type,
            num_people=request.num_people,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))