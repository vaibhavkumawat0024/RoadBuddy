# RoadBuddy 🚗
**AI-Powered Road Trip Planner for India**

RoadBuddy helps Indian travellers plan road trips end-to-end: AI-generated itineraries, fuel & toll cost estimates, route safety checks, a community route-sharing hub, trip journals, and booking across transport (bus/train/flight) and a built-in cab/vehicle provider marketplace.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python) |
| Database | SQLAlchemy ORM + Alembic migrations (PostgreSQL in prod, SQLite for local/test) |
| Auth | JWT (python-jose) + bcrypt password hashing |
| AI | Groq API (Llama models), with mock fallbacks when no API key is set |
| Frontend | Jinja2 server-rendered templates + vanilla JS + Leaflet (maps) |
| Email | SMTP-based OTP verification |

---

## Project Structure

```
RoadBuddy/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, router registration, CORS, startup migrations
│   │   ├── core/                 # config, database, JWT auth, email OTP
│   │   ├── models/models.py      # SQLAlchemy models (Users, Trips, Providers, Bookings, etc.)
│   │   ├── schemas/               # Pydantic request/response models (user-facing trip/journal/etc.)
│   │   ├── routers/               # /api/* JSON endpoints — users, trips, fuel, community, journal, transport, booking
│   │   ├── provider/               # Provider-side system: auth, router (/api/provider/*), schemas, HTML pages
│   │   ├── pages/                  # User-facing HTML page routes (auth, dashboard, plan-trip, etc.)
│   │   └── services/                # Business logic + AI integrations (one mock + one Groq path each)
│   ├── templates/                   # Jinja2 HTML templates
│   ├── static/                      # CSS/JS assets
│   ├── alembic/                     # DB migrations
│   ├── seed_data.py                 # Sample data seeding script
│   └── requirements.txt
├── frontend/                         # Reserved for a future standalone frontend (currently empty)
├── docs/architecture.md
└── infra/
```

---

## Core Features

### Trip Planning (AI)
- **AI itinerary generator** (`POST /api/trips/generate`) — day-by-day plan with stops, costs, season/group/budget awareness
- **AI waypoint suggestions** — hidden gems, dhabas, viewpoints along a route
- **AI route safety analyzer** — hazard flags, safety score, seasonal warnings
- **AI trip chatbot** — conversational trip-planning assistant
- **AI trip recommendations** — personalized suggestions based on interests/budget
- **AI journal summarizer** — turns daily journal entries into a trip story
- **AI smart search** — natural-language community route search

All AI features call **Groq**; every service has a deterministic **mock fallback** so the app works fully offline / without an API key.

### Fuel & Cost
- Fuel cost + toll estimate calculator (`/api/fuel/*`)
- Current fuel price lookup

### Community
- Publish, browse, clone, and review shared routes (`/api/community/*`)

### Trip Journal
- Daily entries with expense tracking and AI-generated trip summaries (`/api/journal/*`)

### Transport & Booking
- Search/book buses, trains, and flights (`/api/transport/*`, `/api/booking/*`) — mock data, structured for real provider API integration later

### Cab / Vehicle Provider Marketplace
A two-sided system layered on top of the rider-facing app:
- **Providers** (cab owners, rental companies, bus/traveller operators) register, complete an onboarding "Quick Setup" (service type + booking mode), and list vehicles through a dedicated dashboard (`/provider/*` pages, `/api/provider/*` API).
- Vehicles are listed either as **private** (distance-based, price-per-km, available from a city) or **route-based/public** (fixed origin → destination, schedule, fixed fare).
- **`GET /api/provider/services`** lists all active vehicles across every provider — private cabs, company/operator fleets, and self-drive rentals together — for the rider-facing **Cab tab** on the Plan Trip page, regardless of exact route match.
- Riders can book directly via `POST /api/provider/book`.

---

## Database Models

`User`, `Vehicle`, `Trip`, `TripStop`, `TransportOption`, `Booking`, `CommunityRoute`, `RouteReview`, `Journal`, `JournalEntry`, `Hotel`/`HotelBooking`, `Train`/`TrainBooking`, `Bus`/`BusBooking`, `Flight`/`FlightBooking`, `Provider`, `ProviderVehicle`, `ProviderBooking`.

---

## API Overview

| Router | Prefix | Highlights |
|---|---|---|
| `users` | `/api/users` | register, login, profile, vehicles |
| `trips` | `/api/trips` | generate (AI), my trips, cost, waypoints, chat, safety-check, recommendations |
| `fuel` | `/api/fuel` | calculate, fuel-prices, toll-estimate |
| `community` | `/api/community` | publish/browse/clone routes, reviews, AI smart-search |
| `journal` | `/api/journal` | entries, publish, expense summary, AI summarize |
| `transport` | `/api/transport` | search, book, my bookings, cancel |
| `booking` | `/api/booking` | hotel/train/bus/flight search + book |
| `provider` | `/api/provider` | register, login, vehicle CRUD, **services** (public listing), search, book |

Full interactive docs at **`/docs`** once the server is running.

---

## Web Pages

| Page | URL |
|---|---|
| Register / Login (OTP-verified) | `/register`, `/login` |
| Dashboard | `/dashboard` |
| Plan Trip (map, AI itinerary, transit tabs incl. Cab) | `/plan-trip` |
| My Trips | `/my-trips` |
| My Vehicles | `/add-vehicle` |
| Community | `/community` |
| Profile | `/profile` |
| Provider Register/Login/Dashboard/Vehicles/Bookings | `/provider/*` |

---

## Authentication

```
Register → Email OTP verification → Login → JWT (httponly cookie / Bearer token) → Protected routes
```
- Passwords hashed with **bcrypt**
- JWT signed with `SECRET_KEY`, default 24-hour expiry
- Providers have a **separate** auth system (`app/provider/auth.py`) from riders

---

## Environment Variables

```
DATABASE_URL         # PostgreSQL connection string (or sqlite:///./test.db for local dev)
SECRET_KEY           # JWT signing secret
GROQ_API_KEY         # optional — enables real AI responses; falls back to mocks if unset
MAIL_USERNAME        # optional — SMTP sender for OTP emails
MAIL_PASSWORD
MAIL_FROM
```

---

## Running Locally

```bash
git clone https://github.com/<your-org>/RoadBuddy.git
cd RoadBuddy/backend

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

# create a .env with at least DATABASE_URL and SECRET_KEY
uvicorn app.main:app --reload
```

Then open:
- `http://localhost:8000/dashboard` — rider app
- `http://localhost:8000/provider/dashboard` — provider portal
- `http://localhost:8000/docs` — interactive API reference

---

## Work Division

### Kunal (AI & Frontend)
- Built all 7 AI services from scratch
- Upgraded AI trip planner with season/group/budget context
- Built AI waypoint suggester
- Built AI trip chatbot with multi-turn conversation
- Built AI journal summarizer
- Built AI route safety analyzer
- Built AI smart search
- Built AI trip recommendations
- Upgraded dashboard with AI feature widgets
- Built Plan Trip page (4 steps)
- Built My Trips page
- Built Add Vehicle page
- Built Community page
- Built Profile page
- Added maps and booking links
- Fixed CI/CD pipeline (GitHub Actions)
- Helped with Render deployment

### Vaibhav (Backend & Database)
- FastAPI project setup and structure
- JWT authentication with bcrypt
- User registration and login
- Vehicle management API
- Fuel and toll calculator
- Transport booking (bus/train/flight)
- Database setup
- Database tables and migrations (Alembic)
- Automated test suite
- Community routes module
- Trip journal module
- Provider / cab marketplace backend (`/api/provider/*`)
- HTML templates (base, login, register, dashboard, etc.)

---

## Known Gaps / Next Steps

| Item | Notes |
|---|---|
| Real maps/routing | Currently OpenStreetMap/OSRM (free) — swap for Google Maps if paid routing is needed |
| Real transport/hotel data | Bus/train/flight/hotel search is mock data, structured for real API integration |
| Rider auth on provider booking | `POST /api/provider/book` doesn't yet attach the logged-in rider's real user ID |
| Payments | Not integrated yet |
| Push notifications, photo uploads | Not yet implemented |

---

*RoadBuddy — Plan smarter, travel better.*