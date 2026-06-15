from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import User, Trip, Vehicle

from passlib.context import CryptContext


router = APIRouter()

templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ---------------- USER FROM COOKIE ----------------

def get_user_from_cookie(request: Request, db: Session):

    token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        from jose import jwt
        from app.core.config import settings

        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"]
        )

        user = db.query(User).filter(
            User.id == int(payload["sub"])
        ).first()

        return user

    except Exception:
        return None



# ---------------- DASHBOARD ----------------


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_user_from_cookie(request, db)

    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )


    trips = db.query(Trip).filter(
        Trip.user_id == user.id
    ).order_by(
        Trip.created_at.desc()
    ).limit(5).all()


    vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == user.id
    ).all()


    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "trips": trips,
            "trip_count": len(trips),
            "vehicle_count": len(vehicles)
        }
    )



# ---------------- PLAN TRIP ----------------


@router.get("/plan-trip", response_class=HTMLResponse)
def plan_trip_page(
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_user_from_cookie(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)


    vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == user.id
    ).all()


    token = request.cookies.get("access_token")


    return templates.TemplateResponse(
        request,
        "plan_trip.html",
        {
            "user": user,
            "vehicles": vehicles,
            "token": token
        }
    )



# ---------------- ADD VEHICLE ----------------


@router.get("/add-vehicle", response_class=HTMLResponse)
def add_vehicle_page(
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_user_from_cookie(request, db)

    if not user:
        return RedirectResponse("/login", status_code=303)


    vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == user.id
    ).all()


    return templates.TemplateResponse(
        request,
        "add_vehicle.html",
        {
            "user": user,
            "vehicles": vehicles
        }
    )



@router.post("/add-vehicle")
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
        return RedirectResponse("/login")


    vehicle = Vehicle(
        user_id=user.id,
        name=name,
        fuel_type=fuel_type,
        category=category,
        mileage_kmpl=mileage_kmpl
    )


    db.add(vehicle)
    db.commit()


    return RedirectResponse(
        "/add-vehicle",
        status_code=303
    )



# ---------------- MY TRIPS ----------------


@router.get("/my-trips", response_class=HTMLResponse)
def my_trips_page(
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_user_from_cookie(request, db)

    if not user:
        return RedirectResponse("/login")


    from app.models.models import TripStop


    trips = db.query(Trip).filter(
        Trip.user_id == user.id
    ).order_by(
        Trip.created_at.desc()
    ).all()


    for trip in trips:

        trip.stops = db.query(TripStop).filter(
            TripStop.trip_id == trip.id
        ).all()


    return templates.TemplateResponse(
        request,
        "my_trips.html",
        {
            "user": user,
            "trips": trips
        }
    )



# ---------------- COMMUNITY ----------------


@router.get("/community", response_class=HTMLResponse)
async def community_page(
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_user_from_cookie(request, db)


    return templates.TemplateResponse(
        request,
        "community.html",
        {
            "user": user
        }
    )



# ---------------- PROFILE ----------------


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: Session = Depends(get_db)
):

    user = get_user_from_cookie(
        request,
        db
    )


    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )


    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "user": user
        }
    )



@router.post("/profile/update")
async def update_profile(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    db: Session = Depends(get_db)
):

    user = get_user_from_cookie(
        request,
        db
    )


    if not user:
        return RedirectResponse(
            "/login",
            status_code=303
        )


    user.name = name
    user.email = email


    if password:

        user.hashed_password = pwd_context.hash(
            password
        )


    db.commit()


    return RedirectResponse(
        "/profile",
        status_code=303
    )