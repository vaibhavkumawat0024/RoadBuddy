from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core import api_client
from app.core.config import AUTH_COOKIE_NAME

router = APIRouter()

def _get_token(request: Request) -> Optional[str]:
    return request.cookies.get(AUTH_COOKIE_NAME)

def _get_provider_token(request: Request) -> Optional[str]:
    return request.cookies.get("food_provider_access_token") or request.cookies.get("provider_access_token")


# ── Pydantic proxy schemas ──────────────────────────────────────────────────

class FoodOrderItemProxy(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    price: float

class OrderCreateProxy(BaseModel):
    restaurant_id: int
    items: List[FoodOrderItemProxy]
    total_amount: float
    payment_method: str = "prepaid"

class ArrivalUpdateProxy(BaseModel):
    arrival_time_mins: int

class ReviewCreateProxy(BaseModel):
    rating: int
    comment: str

class MenuItemCreateProxy(BaseModel):
    name: str
    description: str
    price_inr: float
    category: str = "Veg"


# ── Traveler Proxy Routes ───────────────────────────────────────────────────

@router.get("/food/restaurants")
async def get_restaurants(city: str, request: Request):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.get_restaurants(token, city)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/food/restaurants/{restaurant_id}/menu")
async def get_restaurant_menu(restaurant_id: int, request: Request):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.get_restaurant_menu(token, restaurant_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.post("/food/orders")
async def create_food_order(request: Request, body: OrderCreateProxy):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.create_food_order(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.post("/food/orders/{order_id}/arrival")
async def update_food_order_arrival(order_id: int, request: Request, body: ArrivalUpdateProxy):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.update_food_order_arrival(token, order_id, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.post("/food/menu-items/{item_id}/review")
async def add_menu_item_review(item_id: int, request: Request, body: ReviewCreateProxy):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.add_menu_item_review(token, item_id, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.get("/food/my-orders")
async def get_my_food_orders(request: Request):
    token = _get_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.get_my_food_orders(token)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


# ── Provider Proxy Routes ───────────────────────────────────────────────────

@router.get("/food/provider/orders")
async def get_provider_food_orders(request: Request):
    token = _get_provider_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.get_provider_food_orders(token)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class StatusUpdateBody(BaseModel):
    status: str

@router.patch("/food/provider/orders/{order_id}/status")
async def update_provider_food_order_status(order_id: int, request: Request, body: StatusUpdateBody):
    token = _get_provider_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.update_provider_food_order_status(token, order_id, body.status)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


class PrepTimeUpdateBody(BaseModel):
    prep_time_mins: int

@router.patch("/food/provider/orders/{order_id}/prep-time")
async def update_provider_food_order_prep_time(order_id: int, request: Request, body: PrepTimeUpdateBody):
    token = _get_provider_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.update_provider_food_order_prep_time(token, order_id, body.prep_time_mins)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.post("/food/provider/menu")
async def add_provider_menu_item(request: Request, body: MenuItemCreateProxy):
    token = _get_provider_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.add_provider_menu_item(token, body.model_dump())
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})


@router.delete("/food/provider/menu/{item_id}")
async def delete_provider_menu_item(item_id: int, request: Request):
    token = _get_provider_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized. Please log in."})
    try:
        return await api_client.delete_provider_menu_item(token, item_id)
    except api_client.BackendError as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
