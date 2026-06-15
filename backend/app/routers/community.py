from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.schemas.schemas import RoutePost, RouteReview, RouteOut
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.models import CommunityRoute, RouteReview as RouteReviewModel, User
from typing import Optional
from pydantic import BaseModel

router = APIRouter()


# ── Publish & Browse ──────────────────────────────────────────────────────────

@router.post("/routes", response_model=RouteOut, status_code=201)
def publish_route(
    data: RoutePost,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Share a completed trip as a community route."""

    # Get author name from DB
    user = db.query(User).filter(
        User.id == int(current_user["user_id"])
    ).first()
    author_name = user.name if user else "Traveler"

    route = CommunityRoute(
        user_id     = int(current_user["user_id"]),
        trip_id     = data.trip_id,
        title       = data.title,
        description = data.description,
        tags        = ",".join(data.tags),
        is_public   = data.is_public,
        origin      = "Unknown",
        destination = "Unknown",
        avg_rating  = 0.0,
        total_reviews = 0,
        clone_count = 0,
    )
    db.add(route)
    db.commit()
    db.refresh(route)

    return RouteOut(
        id            = str(route.id),
        title         = route.title,
        origin        = route.origin,
        destination   = route.destination,
        description   = route.description,
        tags          = route.tags.split(",") if route.tags else [],
        avg_rating    = route.avg_rating,
        total_reviews = route.total_reviews,
        clone_count   = route.clone_count,
        author_name   = author_name,
    )


@router.get("/routes", response_model=list[RouteOut])
def browse_routes(
    tag: Optional[str] = Query(None, description="Filter by tag e.g. scenic"),
    min_rating: float = Query(0, ge=0, le=5, description="Minimum star rating"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Browse all public community routes."""
    routes = db.query(CommunityRoute).filter(
        CommunityRoute.is_public == True,
        CommunityRoute.avg_rating >= min_rating,
    ).limit(limit).all()

    results = []
    for r in routes:
        tags_list = r.tags.split(",") if r.tags else []
        if tag and tag.lower() not in [t.lower() for t in tags_list]:
            continue
        results.append(RouteOut(
            id            = str(r.id),
            title         = r.title,
            origin        = r.origin,
            destination   = r.destination,
            description   = r.description,
            tags          = tags_list,
            avg_rating    = r.avg_rating,
            total_reviews = r.total_reviews,
            clone_count   = r.clone_count,
            author_name   = r.user.name if r.user else "Traveler",
        ))
    return results


@router.get("/routes/{route_id}", response_model=RouteOut)
def get_route(route_id: str, db: Session = Depends(get_db)):
    """Get a single community route by ID."""
    try:
        rid = int(route_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Route not found")
    route = db.query(CommunityRoute).filter(
        CommunityRoute.id == rid
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    return RouteOut(
        id            = str(route.id),
        title         = route.title,
        origin        = route.origin,
        destination   = route.destination,
        description   = route.description,
        tags          = route.tags.split(",") if route.tags else [],
        avg_rating    = route.avg_rating,
        total_reviews = route.total_reviews,
        clone_count   = route.clone_count,
        author_name   = route.user.name if route.user else "Traveler",
    )


# ── Clone ─────────────────────────────────────────────────────────────────────

@router.post("/routes/{route_id}/clone")
def clone_route(
    route_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clone someone else's route to your saved trips."""
    route = db.query(CommunityRoute).filter(
        CommunityRoute.id == int(route_id)
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    route.clone_count += 1
    db.commit()

    return {
        "message": f"Route '{route.title}' cloned to your saved trips!",
        "route_id": route_id,
        "cloned_by": current_user["user_id"],
    }


# ── Reviews ───────────────────────────────────────────────────────────────────

@router.post("/routes/{route_id}/review", status_code=201)
def add_review(
    route_id: str,
    data: RouteReview,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Post a star rating and review for a route."""
    route = db.query(CommunityRoute).filter(
        CommunityRoute.id == int(route_id)
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    if not 1 <= data.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    review = RouteReviewModel(
        route_id    = int(route_id),
        user_id     = int(current_user["user_id"]),
        rating      = data.rating,
        review_text = data.review_text,
        tags        = ",".join(data.tags),
    )
    db.add(review)

    # Recalculate average rating
    all_reviews = db.query(RouteReviewModel).filter(
        RouteReviewModel.route_id == int(route_id)
    ).all()
    all_ratings = [r.rating for r in all_reviews] + [data.rating]
    route.avg_rating    = round(sum(all_ratings) / len(all_ratings), 1)
    route.total_reviews = len(all_ratings)

    db.commit()
    db.refresh(review)

    return {
        "message": "Review submitted!",
        "review": {
            "id": str(review.id),
            "rating": review.rating,
            "review_text": review.review_text,
        }
    }


@router.get("/routes/{route_id}/reviews")
def get_reviews(route_id: str, db: Session = Depends(get_db)):
    """Get all reviews for a route."""
    route = db.query(CommunityRoute).filter(
        CommunityRoute.id == int(route_id)
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    reviews = db.query(RouteReviewModel).filter(
        RouteReviewModel.route_id == int(route_id)
    ).all()

    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "rating": r.rating,
            "review_text": r.review_text,
            "tags": r.tags.split(",") if r.tags else [],
        }
        for r in reviews
    ]


# ── Smart Search ──────────────────────────────────────────────────────────────

class SmartSearchRequest(BaseModel):
    query: str


@router.post("/smart-search")
async def ai_smart_search(request: SmartSearchRequest):
    """AI-powered natural language search for community routes."""
    try:
        from app.services.smart_search import smart_search
        result = await smart_search(query=request.query)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))