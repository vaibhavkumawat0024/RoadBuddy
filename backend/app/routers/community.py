from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.schemas import RoutePost, RouteReview, RouteOut
from app.core.auth import get_current_user
from typing import Optional
from app.services.smart_search import smart_search
from pydantic import BaseModel
router = APIRouter()

# In-memory stores (replace with PostgreSQL in production)
_routes: dict  = {}
_reviews: dict = {}    # route_id -> list of reviews


# ── Publish & Browse ──────────────────────────────────────────────────────────

@router.post("/routes", response_model=RouteOut, status_code=201)
def publish_route(data: RoutePost, current_user: dict = Depends(get_current_user)):
    """Share a completed trip as a community route."""
    route_id = f"r_{len(_routes) + 1}"
    route = {
        "id": route_id,
        "user_id": current_user["user_id"],
        "author_name": "Traveler",       # In production: fetch name from DB
        "trip_id": data.trip_id,
        "title": data.title,
        "description": data.description,
        "tags": data.tags,
        "is_public": data.is_public,
        "origin": "Unknown",             # In production: fetch from trip
        "destination": "Unknown",
        "avg_rating": 0.0,
        "total_reviews": 0,
        "clone_count": 0,
    }
    _routes[route_id] = route
    return RouteOut(**route)


@router.get("/routes", response_model=list[RouteOut])
def browse_routes(
    tag: Optional[str] = Query(None, description="Filter by tag e.g. scenic"),
    min_rating: float = Query(0, ge=0, le=5, description="Minimum star rating"),
    limit: int = Query(20, le=100),
):
    """Browse all public community routes. Filter by tag or rating."""
    results = [
        r for r in _routes.values()
        if r["is_public"]
        and r["avg_rating"] >= min_rating
        and (tag is None or tag.lower() in [t.lower() for t in r["tags"]])
    ]
    return [RouteOut(**r) for r in results[:limit]]


@router.get("/routes/{route_id}", response_model=RouteOut)
def get_route(route_id: str):
    """Get a single community route by ID."""
    route = _routes.get(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return RouteOut(**route)


# ── Clone ─────────────────────────────────────────────────────────────────────

@router.post("/routes/{route_id}/clone")
def clone_route(route_id: str, current_user: dict = Depends(get_current_user)):
    """
    Clone someone else's route to your saved trips.
    Increments the clone counter on the original route.
    """
    route = _routes.get(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route["clone_count"] += 1
    # In production: create a new trip record for this user based on the route
    return {
        "message": f"Route '{route['title']}' cloned to your saved trips!",
        "route_id": route_id,
        "cloned_by": current_user["user_id"],
    }


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.post("/routes/{route_id}/review", status_code=201)
def add_review(route_id: str, data: RouteReview, current_user: dict = Depends(get_current_user)):
    """Post a star rating and review for a route."""
    if route_id not in _routes:
        raise HTTPException(status_code=404, detail="Route not found")
    if not 1 <= data.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    if route_id not in _reviews:
        _reviews[route_id] = []

    review = {
        "id": f"rev_{len(_reviews[route_id]) + 1}",
        "user_id": current_user["user_id"],
        "rating": data.rating,
        "review_text": data.review_text,
        "tags": data.tags,
    }
    _reviews[route_id].append(review)

    # Recalculate average rating
    all_ratings = [r["rating"] for r in _reviews[route_id]]
    _routes[route_id]["avg_rating"] = round(sum(all_ratings) / len(all_ratings), 1)
    _routes[route_id]["total_reviews"] = len(all_ratings)

    return {"message": "Review submitted!", "review": review}


@router.get("/routes/{route_id}/reviews")
def get_reviews(route_id: str):
    """Get all reviews for a route."""
    if route_id not in _routes:
        raise HTTPException(status_code=404, detail="Route not found")
    return _reviews.get(route_id, [])

class SmartSearchRequest(BaseModel):
    query: str


@router.post("/smart-search")
async def ai_smart_search(request: SmartSearchRequest):
    """
    AI-powered natural language search for community routes.
    Example: "beach trip under 5000" or "family trip to hill station 3 days"
    """
    try:
        result = await smart_search(query=request.query)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
