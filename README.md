# RoadBuddy 🚗
**AI-Powered Road Trip Planner for India**

RoadBuddy is a modern, unified web platform designed to help travellers in India plan and manage road trips end-to-end. It features AI-generated day-by-day itineraries, fuel and toll cost calculations, route safety assessments, community route sharing, personal trip journals with summaries, and an integrated travel marketplace supporting transit bookings (bus, train, flight, hotel) and a partner-run cab/vehicle provider fleet.

---

## 📱 Mobile-First Responsive Design & Maps Cockpit

RoadBuddy is engineered with a **mobile-first design philosophy**:
- **Full Viewport Map Canvas**: Map displays dynamically across 100% of mobile viewports with smooth touch gestures, pinch-to-zoom, and safe area insets (`env(safe-area-inset-top)`).
- **Floating Bottom Drawer Sheet**: Controls and directions collapse into an intuitive bottom drawer sheet (`max-height: 45vh`), preserving maximum map visibility for drivers on mobile screens.
- **Reverse Geocoded City Names**: Hides raw lat/lon coordinates (`26.9115, 75.7297`), displaying clean, human-readable city/area names (`Jaipur`, `Delhi`, `Manali`).
- **Touch-Friendly Controls**: Minimum 44px tap targets, sleek pill action buttons, and responsive topbar headers.
- **Uncluttered Navigation View Mode**: Automatically hides control sidebars, layer toggles, and unnecessary buttons when viewing completed trip routes or hotel navigation.

---

## Architectural Overview

RoadBuddy is built as a **monolithic unified architecture** where a single FastAPI service handles both business logic REST APIs and compiles/renders traveler/partner Jinja2 HTML page templates.

```
+-------------------------------------------------------------+
|                     ROADBUDDY APPLICATION                   |
|                          (Port 8000)                        |
|                                                             |
|   +-----------------------+       +---------------------+   |
|   |   JINJA2 TEMPLATES    | <===> |    REST API LAYER   |   |
|   | (Traveler & Provider) |       | (FastAPI Routers)   |   |
|   +-----------------------+       +---------------------+   |
|               ^                               ^             |
|               |                               |             |
|               v                               v             |
|   +-----------------------------------------------------+   |
|   |         SQLAlchemy ORM + SQLite / PostgreSQL        |   |
|   +-----------------------------------------------------+   |
+-------------------------------------------------------------+
```

### Key Architectural Features:
1. **Unified Service**: Both traveler-facing pages (explore, planner, dashboard) and provider portals (dispatch cockpit, dhaba order desk) are served from port 8000.
2. **Interactive Mapbox GL JS v3 Engine**: High-performance vector tiles, Mapbox Geocoding API (`api.mapbox.com/geocoding/v5/mapbox.places`), Mapbox Directions API, 3D building extrusions, and DEM terrain elevation.
3. **Robust Auth & Security**: Traveler and provider sessions are managed via HttpOnly JWT cookies (`roadbuddy_token` and `access_token`).

---

## Tech Stack

| Component | Technology | Status |
|---|---|---|
| **Server Engine** | FastAPI (Python 3.10+) running on port 8000 | ✅ **Fully Operational** |
| **Styling & Presentation** | Vanilla CSS + Tailwind CSS (glassmorphism, mobile drawer bottom sheets) | ✅ **Available** |
| **Interactive Mapping** | Mapbox GL JS v3 (Vector tiles, Driving-Traffic routing, Geocoding API, DEM 3D Terrain) | ✅ **Available** |
| **Database & ORM** | SQLAlchemy ORM with SQLite (development) and PostgreSQL compatibility | ✅ **Available** |
| **Authentication** | JWT (python-jose) + bcrypt hashing (secured **HttpOnly** cookies) | ✅ **Available** |
| **AI Processing** | Groq API (Llama-3.1 models) with fallback to Gemini API | ✅ **Available** |
| **Email Dispatch** | SMTP-based Brevo API for OTP verification | ✅ **Available** |

---

## Core Features & Modules

### 1. AI-Powered Trip Planning & Custom Itineraries
- **Itinerary Generator** (`POST /api/trips/generate`): Generates custom day-by-day plans specifying stops, estimated budgets, and travel tips tailored to season, group composition, and budget tier.
- **Vehicle-Aware Costs**: Integrates vehicle specifications (category, fuel type, mileage/KMPL) to dynamically calculate fuel costs (Petrol, Diesel, CNG, EV) and toll rates.
- **4-Slot Daily Timeline**: Plans are divided into 4 slots per day: `morning`, `afternoon`, `evening`, and `night`.
- **Route Safety Checks**: Evaluates route safety profiles, terrain hazards, and assigns weather/seasonal safety scores.

### 2. Intelligent Mobile Mapping & Navigation
- **Automatic Driving Path Rendering**: Instantly resolves destination city coordinates via Mapbox Geocoding API and draws blue driving traffic routes without requiring manual form clicks.
- **Google Maps-style Navigation HUD**: Turn-by-turn instruction banner, simulated heading arrow marker, and dynamic compass.
- **Clean View Route Mode**: Clean view mode for saved/completed trips that hides clutter while retaining essential navigation controls.

### 3. Traveler Garage & Vehicle Profiles
- Register personal vehicles to compute fuel efficiency and custom ranges.

### 4. Cab Services & Provider Marketplace
- Fleet vehicles separated into Private Cabs (per km) and Fixed-Fare Cabs (routes).
- Multi-seat booking modal featuring passenger name/age registration forms stored as serialized JSON.

---

## Project Structure

```
RoadBuddy/
├── backend/                             # FastAPI Application root directory
│   ├── app/
│   │   ├── main.py                      # FastAPI initialization, routers, CORS and custom exception handlers
│   │   ├── core/                        # Config, database connections, JWT auth, and OTP utils
│   │   ├── models/                      # Database declarations (SQLAlchemy models)
│   │   ├── schemas/                     # Pydantic schemas for core entities & transit bookings
│   │   ├── provider/                    # Provider marketplace engine (Fleet CRUD, Setup, telemetry)
│   │   ├── routers/                     # Traveler JSON API endpoints (trips, users, fuel, journals)
│   │   └── services/                    # AI services, Groq clients, and fuel calculators
│   ├── templates/                       # Jinja2 views styled for mobile & desktop responsiveness
│   │   ├── start_trip.html              # Mobile-first Smart Route Map & Navigation view
│   │   ├── dashboard.html               # Traveler Dashboard & Widgets pane
│   │   ├── trip_itinerary.html          # Detailed AI Trip Itinerary & Route link
│   │   ├── plan_trip.html               # AI Trip Planning form with reverse-geocoded GPS
│   │   └── ...                          # Traveler & Provider dashboard templates
│   ├── static/                          # Custom stylesheets and graphics
│   ├── seed_data.py                     # Mock transit schedules seeding script
│   ├── seed_restaurants.py              # Mock restaurants & menu items seeding script
│   └── requirements.txt                 # Backend package requirements
└── README.md                            # Comprehensive project guide
```

---

## Database Models

- `User`: Traveler logins, vehicles list, active bookings.
- `Vehicle`: Personal vehicle specifications in traveler garages.
- `Provider`: Partner businesses, contacts, city, service profiles.
- `ProviderVehicle`: Active vehicle listings deployed for private hire or routes.
- `Trip` & `TripStop`: Saved itineraries and day plans.
- `CommunityRoute` & `RouteReview`: Public route-sharing hub entries.
- `Journal` & `JournalEntry`: Traveler expense sheets and daily diaries.
- `HotelBooking`, `TrainBooking`, `BusBooking`, `FlightBooking`: Core transit tickets.
- `Restaurant`, `MenuItem`, `FoodOrder`, `FoodReview`: Partner dhabas and food catalog system.

---

## Local Execution Guide

### 1. Launch the Unified Service
1. Navigate to the backend directory:
   ```bash
   cd RoadBuddy/backend
   ```
2. Activate your virtual environment and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Seed initial mock records:
   ```bash
   python seed_data.py
   python seed_restaurants.py
   ```
4. Spin up the FastAPI web server:
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```

### 2. Access URLs
- **Web App & Dashboards**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive REST API Reference**: [http://localhost:8000/docs](http://localhost:8000/docs)