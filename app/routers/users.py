from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.schemas import UserCreate, UserLogin, UserOut, TokenOut, VehicleCreate, VehicleOut
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()

# ── In-memory "database" for development ──────────────────────────────────────
# Replace these dicts with real DB queries (SQLAlchemy / Tortoise ORM) later.
_users: dict    = {}   # email -> user record
_vehicles: dict = {}   # user_id -> list of vehicles


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserOut, status_code=201)
def register(data: UserCreate):
    """Create a new user account."""
    if data.email in _users:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = f"u_{len(_users) + 1}"
    _users[data.email] = {
        "id": user_id,
        "name": data.name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "home_city": data.home_city,
        "total_trips": 0,
    }
    u = _users[data.email]
    return UserOut(id=u["id"], name=u["name"], email=u["email"], home_city=u["home_city"])


@router.post("/login", response_model=TokenOut)
def login(data: UserLogin):
    """Log in and get a JWT access token."""
    user = _users.get(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["id"]})
    return TokenOut(access_token=token)


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def get_profile(current_user: dict = Depends(get_current_user)):
    """Get the logged-in user's profile."""
    # In production: query DB by current_user["user_id"]
    for user in _users.values():
        if user["id"] == current_user["user_id"]:
            return UserOut(**{k: user[k] for k in UserOut.model_fields})
    raise HTTPException(status_code=404, detail="User not found")


# ── Vehicles ──────────────────────────────────────────────────────────────────

@router.post("/vehicles", response_model=VehicleOut, status_code=201)
def add_vehicle(data: VehicleCreate, current_user: dict = Depends(get_current_user)):
    """Add a vehicle to the user's garage."""
    user_id = current_user["user_id"]
    if user_id not in _vehicles:
        _vehicles[user_id] = []

    vehicle_id = f"v_{user_id}_{len(_vehicles[user_id]) + 1}"
    vehicle = {"id": vehicle_id, "user_id": user_id, **data.model_dump()}
    _vehicles[user_id].append(vehicle)
    return VehicleOut(**vehicle)


@router.get("/vehicles", response_model=list[VehicleOut])
def list_vehicles(current_user: dict = Depends(get_current_user)):
    """List all vehicles for the logged-in user."""
    user_id = current_user["user_id"]
    return [VehicleOut(**v) for v in _vehicles.get(user_id, [])]
