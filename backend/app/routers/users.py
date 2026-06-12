from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.schemas.schemas import UserCreate, UserOut, TokenOut, VehicleCreate, VehicleOut
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user
from app.core.database import get_db
from app.models.models import User, Vehicle

router = APIRouter()


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name          = data.name,
        email         = data.email,
        password_hash = hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserOut(
        id          = str(user.id),
        name        = user.name,
        email       = user.email,
        home_city   = None,
        total_trips = 0,
    )


@router.post("/login", response_model=TokenOut)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Log in and get a JWT access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id)})
    return TokenOut(access_token=token)


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the logged-in user's profile."""
    user = db.query(User).filter(
        User.id == int(current_user["user_id"])
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(
        id          = str(user.id),
        name        = user.name,
        email       = user.email,
        home_city   = None,
        total_trips = len(user.trips),
    )


# ── Vehicles ──────────────────────────────────────────────────────────────────

@router.post("/vehicles", response_model=VehicleOut, status_code=201)
def add_vehicle(
    data: VehicleCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a vehicle to the user's garage."""
    vehicle = Vehicle(
        user_id      = int(current_user["user_id"]),
        name         = data.name,
        fuel_type    = data.fuel_type,
        category     = data.category,
        mileage_kmpl = data.mileage_kmpl,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return VehicleOut(
        id           = str(vehicle.id),
        user_id      = str(vehicle.user_id),
        name         = vehicle.name,
        fuel_type    = vehicle.fuel_type,
        category     = vehicle.category,
        mileage_kmpl = vehicle.mileage_kmpl,
    )


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all vehicles for the logged-in user."""
    vehicles = db.query(Vehicle).filter(
        Vehicle.user_id == int(current_user["user_id"])
    ).all()

    return [
        VehicleOut(
            id           = str(v.id),
            user_id      = str(v.user_id),
            name         = v.name,
            fuel_type    = v.fuel_type,
            category     = v.category,
            mileage_kmpl = v.mileage_kmpl,
        )
        for v in vehicles
    ]