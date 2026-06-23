from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional

from app.core import api_client
from app.core.config import AUTH_COOKIE_NAME

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _get_token(request: Request) -> Optional[str]:
    return request.cookies.get(AUTH_COOKIE_NAME)


@router.get("/journal/{trip_id}", response_class=HTMLResponse)
async def journal_page(request: Request, trip_id: str):
    token = _get_token(request)
    if not token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")

    journal = None
    summary = None
    error = None

    # Try fetching existing journal for this trip
    try:
        journal = await api_client.get_journal(token, trip_id)
        summary = await api_client.get_journal_summary(token, trip_id)
    except api_client.BackendError as e:
        if e.status_code == 404:
            # No journal created yet, that is fine, UI will show add entry form
            pass
        else:
            error = e.detail

    # Find the trip details from user's trips list to get origin/destination/dates
    trip_details = None
    try:
        trips = await api_client.list_my_trips(token)
        for t in trips:
            if str(t.get("id")) == trip_id:
                trip_details = t
                break
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "journal.html",
        {
            "request": request,
            "trip_id": trip_id,
            "journal": journal,
            "summary": summary,
            "trip": trip_details,
            "error": error,
        },
    )


class JournalEntryBody(BaseModel):
    trip_id: str
    stop_name: str
    notes: Optional[str] = None
    expense_inr: Optional[float] = 0.0
    lat: Optional[float] = None
    lng: Optional[float] = None


@router.post("/journal/entry")
async def add_journal_entry(request: Request, body: JournalEntryBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.add_journal_entry(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.patch("/journal/{trip_id}/publish")
async def publish_journal(request: Request, trip_id: str):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.publish_journal(token, trip_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/journal/{trip_id}/summary")
async def get_journal_summary(request: Request, trip_id: str):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.get_journal_summary(token, trip_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class JournalSummarizerEntry(BaseModel):
    day: int
    date: Optional[str] = ""
    location: Optional[str] = ""
    mood: Optional[str] = "neutral"
    text: str
    expenses_inr: Optional[float] = 0.0


class SummarizeJournalRequest(BaseModel):
    origin: str
    destination: str
    entries: List[JournalSummarizerEntry]
    total_days: int
    total_cost_inr: Optional[float] = 0.0
    group_type: Optional[str] = "friends"
    num_people: Optional[int] = 2


@router.post("/journal/summarize")
async def summarize_journal(body: SummarizeJournalRequest):
    try:
        return await api_client.summarize_journal(body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
