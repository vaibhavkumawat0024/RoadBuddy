# RoadBuddy AI — FastAPI Backend

## Quick Start

### 1. Create & activate a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Open .env and fill in your API keys (all optional during development)
```

### 4. Run the server
```bash
uvicorn app.main:app --reload
```

### 5. Open the interactive API docs
Visit **http://localhost:8000/docs** — you'll see every endpoint, can test them live.

---

## Project Structure

```
roadbuddy-ai/
├── app/
│   ├── main.py              ← FastAPI app, middleware, router registration
│   ├── core/
│   │   ├── config.py        ← Settings loaded from .env
│   │   └── auth.py          ← JWT helpers, password hashing
│   ├── schemas/
│   │   └── schemas.py       ← All Pydantic request/response models
│   ├── services/
│   │   ├── ai_planner.py    ← Claude/GPT itinerary generation
│   │   └── fuel_calculator.py ← Fuel cost + toll calculation logic
│   └── routers/
│       ├── users.py         ← Register, login, profile, vehicles
│       ├── trips.py         ← AI trip generation + trip CRUD
│       ├── fuel.py          ← Fuel & toll calculator endpoints
│       ├── community.py     ← Route sharing, reviews, clone
│       └── journal.py       ← Trip journal + expense tracking
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints Summary

| Group | Endpoint | What it does |
|---|---|---|
| Auth | POST /api/users/register | Create account |
| Auth | POST /api/users/login | Get JWT token |
| Profile | GET /api/users/me | My profile |
| Vehicles | POST /api/users/vehicles | Add a vehicle |
| Trips | POST /api/trips/generate | Generate AI itinerary |
| Trips | GET /api/trips/{id} | Get a trip |
| Fuel | POST /api/fuel/calculate | Fuel + toll estimate |
| Fuel | GET /api/fuel/fuel-prices | Current fuel prices |
| Community | POST /api/community/routes | Publish a route |
| Community | GET /api/community/routes | Browse routes |
| Community | POST /api/community/routes/{id}/clone | Clone a route |
| Community | POST /api/community/routes/{id}/review | Add a review |
| Journal | POST /api/journal/entry | Add journal entry |
| Journal | GET /api/journal/{trip_id} | View full journal |
| Journal | GET /api/journal/{trip_id}/summary | Expense summary |

## How to use the API (example flow)

```bash
# 1. Register
POST /api/users/register
{"name": "Arjun", "email": "arjun@example.com", "password": "secure123"}

# 2. Login — copy the access_token from the response
POST /api/users/login
{"email": "arjun@example.com", "password": "secure123"}

# 3. Add a vehicle
POST /api/users/vehicles
Authorization: Bearer <token>
{"name": "My Swift", "fuel_type": "petrol", "category": "car", "mileage_kmpl": 18}

# 4. Generate a trip
POST /api/trips/generate
Authorization: Bearer <token>
{
  "origin": "Jaipur, Rajasthan",
  "destination": "Udaipur, Rajasthan",
  "start_date": "2025-12-01",
  "end_date": "2025-12-03",
  "budget_inr": 8000,
  "vehicle_id": "v_u_1_1",
  "group_type": "family",
  "num_people": 4
}
```

## Next Steps (after the basics work)

1. **Add a real database** — install `sqlalchemy` + `asyncpg` and replace the in-memory dicts in each router with actual DB queries.
2. **Add photo uploads** — integrate AWS S3 or Cloudinary for journal photo uploads.
3. **Connect Google Maps** — replace `estimate_distance()` in `fuel_calculator.py` with a real Google Distance Matrix API call.
4. **Add NHAI toll data** — integrate the FASTag API in `fuel_calculator.py` for accurate toll amounts.
