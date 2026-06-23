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


@router.get("/community", response_class=HTMLResponse)
async def community_page(request: Request):
    token = _get_token(request)
    # Get user trips to let them select which trip to publish
    trips = []
    if token:
        try:
            trips = await api_client.list_my_trips(token)
        except Exception:
            pass
    return templates.TemplateResponse(
        request,
        "community.html",
        {"request": request, "trips": trips, "is_logged_in": bool(token)},
    )


@router.get("/community/routes")
async def browse_community_routes(
    tag: Optional[str] = None,
    min_rating: float = 0.0,
    limit: int = 20
):
    try:
        return await api_client.browse_community_routes(tag, min_rating, limit)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/community/routes/{route_id}")
async def get_community_route(route_id: str):
    try:
        return await api_client.get_community_route(route_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class RoutePublishBody(BaseModel):
    trip_id: str
    title: str
    description: str
    tags: List[str] = []
    is_public: bool = True


@router.post("/community/routes")
async def publish_route(request: Request, body: RoutePublishBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.publish_route(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.post("/community/routes/{route_id}/clone")
async def clone_route(request: Request, route_id: str):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.clone_route(token, route_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class RouteReviewBody(BaseModel):
    rating: int
    review_text: str
    tags: List[str] = []


@router.post("/community/routes/{route_id}/review")
async def add_route_review(request: Request, route_id: str, body: RouteReviewBody):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.add_review(token, route_id, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/community/routes/{route_id}/reviews")
async def get_route_reviews(route_id: str):
    try:
        return await api_client.get_reviews(route_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class SmartSearchBody(BaseModel):
    query: str


@router.post("/community/smart-search")
async def ai_smart_search(body: SmartSearchBody):
    try:
        return await api_client.smart_search(body.query)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
