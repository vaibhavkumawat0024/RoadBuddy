from fastapi import APIRouter, Request, Depends
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, Trip, Vehicle

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_user_from_cookie(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user = db.query(User).filter(User.id == int(payload["sub"])).first()
        return user
    except:
        return None


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    trips = db.query(Trip).filter(
        Trip.user_id == user.id
    ).order_by(Trip.created_at.desc()).limit(5).all()

    vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == user.id
    ).all()

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "trips": trips,
        "trip_count": len(trips),
        "vehicle_count": len(vehicles)
    })
@router.get("/plan-trip", response_class=HTMLResponse)
def plan_trip_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == user.id
    ).all()

    # Pass token to template so JS can use it
    token = request.cookies.get("access_token")

    return templates.TemplateResponse(request, "plan_trip.html", {
        "user": user,
        "vehicles": vehicles,
        "token": token,
    })
"""
Add these routes to dashboard_pages.py at the bottom:
"""

@router.get("/add-vehicle", response_class=HTMLResponse)
def add_vehicle_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user.id).all()

    success = request.query_params.get("success")
    return templates.TemplateResponse(request, "add_vehicle.html", {
        "user": user,
        "vehicles": vehicles,
        "success": success,
    })


@router.post("/add-vehicle", response_class=HTMLResponse)
def add_vehicle_submit(
    request: Request,
    name: str = Form(...),
    fuel_type: str = Form(...),
    category: str = Form(...),
    mileage_kmpl: float = Form(...),
    db: Session = Depends(get_db)
):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicle = Vehicle(
        user_id=user.id,
        name=name,
        fuel_type=fuel_type,
        category=category,
        mileage_kmpl=mileage_kmpl,
    )
    db.add(vehicle)
    db.commit()

    return RedirectResponse("/add-vehicle?success=Vehicle added successfully!", status_code=303)


@router.post("/delete-vehicle/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    vehicle = db.query(Vehicle).filter(
        Vehicle.id == vehicle_id,
        Vehicle.user_id == user.id
    ).first()

    if vehicle:
        db.delete(vehicle)
        db.commit()

    return RedirectResponse("/add-vehicle?success=Vehicle deleted.", status_code=303)

@router.get("/my-trips", response_class=HTMLResponse)
def my_trips_page(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
 
    from app.models.models import TripStop
    trips = db.query(Trip).filter(
        Trip.user_id == user.id
    ).order_by(Trip.created_at.desc()).all()
 
    # Attach stops to each trip
    for trip in trips:
        trip.stops = db.query(TripStop).filter(
            TripStop.trip_id == trip.id
        ).order_by(TripStop.day, TripStop.time_slot).all()
 
    return templates.TemplateResponse(request, "my_trips.html", {
        "user": user,
        "trips": trips,
    })
 
 
@router.post("/delete-trip/{trip_id}")
def delete_trip(
    trip_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
 
    from app.models.models import TripStop
    trip = db.query(Trip).filter(
        Trip.id == trip_id,
        Trip.user_id == user.id
    ).first()
 
    if trip:
        db.query(TripStop).filter(TripStop.trip_id == trip.id).delete()
        db.delete(trip)
        db.commit()
 
    return RedirectResponse("/my-trips", status_code=303)