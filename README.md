# RoadBuddy 🚗
**AI-Powered Road Trip Planner for India**

RoadBuddy is a decoupled, modern web platform designed to help travellers in India plan and manage road trips end-to-end. It features AI-generated day-by-day itineraries, fuel and toll cost calculations, route safety assessments, community route sharing, personal trip journals with summaries, and an integrated travel marketplace supporting transit bookings (bus, train, flight, hotel) and a partner-run cab/vehicle provider fleet.

> [!IMPORTANT]
> **Frontend Code Status**: The standalone frontend web application is **Coming Soon** due to some updates and has not been launched for public/end-user release yet. Currently, only the core backend API services (running on Port 8000) are fully operational and ready for use. You can interact with and test all features using the backend interactive API documentation (`/docs`).

---

## Architectural Overview

RoadBuddy is built as a split **decoupled architecture** consisting of two standalone services communicating via asynchronous JSON REST APIs.

*Note: The frontend UI components described here are currently undergoing updates (**Coming Soon**).*

```
+------------------------------------+          JSON REST APIs          +-----------------------------------+
|         STANDALONE FRONTEND        | ===============================> |        CORE API BACKEND           |
|  (Port 3000 - COMING SOON / DEV)   | <=============================== |           (Port 8000)             |
| FastAPI UI + Jinja2 + Leaflet Maps |                                  |  FastAPI + SQLAlchemy + DB + AI   |
+------------------------------------+                                  +-----------------------------------+
```

### Key Architectural Updates:
1. **Presentation Layer Separation**: The traveler-facing and partner-facing web pages run on a standalone FastAPI server on port 3000 (`frontend`), isolated from the backend business logic and database.
2. **CORS & Proxying**: The frontend communicates with the backend via an asynchronous HTTPX client [api_client.py](file:///C:/Users/mahen/RoadBuddy/frontend/app/core/api_client.py). Where necessary (e.g. coordinates tracking, AJAX deletions), the frontend implements local controller proxy routers to bypass browser CORS policies.
3. **Graceful Connection Resilience**: The core API client intercepts `httpx.RequestError` globally. If the backend service goes offline, the frontend catches the 503 service status and renders clean warning overlays rather than crashing with unhandled ASGI 500 error pages.

---

## Tech Stack

| Component | Technology | Status |
|---|---|---|
| **Frontend UI Server** | FastAPI (Python) running on port 3000 | ⏳ **Coming Soon (Undergoing Updates)** |
| **Backend API Server** | FastAPI (Python) running on port 8000 | ✅ **Available & Fully Functional** |
| **Styling & Presentation** | Tailwind CSS + custom glassmorphic cockpit designs with full mobile-responsive breakpoints | ⏳ **Coming Soon (Undergoing Updates)** |
| **Interactive Mapping** | Leaflet.js (OpenStreetMap + OSRM Routing Engines) with custom route corridors | ⏳ **Coming Soon (Undergoing Updates)** |
| **Database & ORM** | SQLAlchemy ORM with SQLite (development/testing) and PostgreSQL compatibility | ✅ **Available** |
| **Authentication** | JWT (python-jose) + bcrypt hashing (isolated session cookies: `roadbuddy_token` for travelers, `provider_access_token` for partners) | ✅ **Available** |
| **AI Processing** | Groq API (Llama models) with local mock fallback configurations for offline development | ✅ **Available** |
| **Email Dispatch** | SMTP-based OTP code verification | ✅ **Available** |

---

## Core Features & Modules

### 1. AI-Powered Trip Planning & Custom Itineraries
- **Itinerary Generator** (`POST /api/trips/generate`): Generates custom day-by-day plans specifying stops, estimated budgets, and travel tips tailored to season, group composition, and budget tier.
- **Vehicle-Aware Costs**: Itinerary generation integrates vehicle-specific specifications (category, fuel type, mileage/KMPL) to dynamically calculate realistic fuel costs (Petrol, Diesel, CNG, or Electric charging rates) and toll rates.
- **Day & Night 4-Slot Timeline**: Plans are divided into 4 slots per day: `morning`, `afternoon`, `evening`, and `night` (covering night bazaars, stargazing, dinner, and hotel check-ins).
- **Rich Waypoint Suggestion**: Custom 40+ word description paragraphs for every stop featuring travel tips, dhaba recommendations, and local highlights.
- **Route Safety Checks**: Evaluates route safety profiles, flags terrain hazards, and assigns a safety score based on weather or seasonal conditions.
- **Conversational Chatbot**: An interactive chatbot helper residing in the dashboard for real-time travel planning suggestions. (Automatically hidden on itinerary pages for clutter-free views).

### 2. Intelligent Mapping & Navigation (Telemetry & Live GPS)
- Interactive Leaflet-based planner with reverse-geocoding coordinates capture.
- **Google Maps-style navigation HUD**: Integrates compass widgets, cardinal telemetry bearings, turn-by-turn instruction boxes, and a pulse user location arrow on `start_trip.html`.
- **Highway Partner Dhabas on Maps**: Database food provider restaurants are plotted on the Leaflet map automatically as green markers with gold stars (`🌟`) and a pulse animation. Popups calculate geodesic distance from the traveler's active location in real-time (e.g. `🚗 12.4 km away`) and provide a "🛒 View Menu & Order" button to place food orders on the go.
- **Overpass POI Search**: Dynamic 3km corridor query along active polyline route paths for Petrol Pumps, Hotels, General Restaurants, Hospitals, and Attractions.

### 3. Traveler Garage & Vehicle Profiles
- Travelers can register personal vehicles to compute fuel efficiency and custom ranges.
- **Dynamic Deletion**: Provides a vehicle deletion route `DELETE /api/users/vehicles/{vehicle_id}` allowing riders to remove cars directly from their garage dashboard using dynamic AJAX.

### 4. Cab Services & Provider Marketplace
A double-sided marketplace that links local travel operators and driver fleets with travelers:
- **Onboarding Setup**: Registered providers configure their company details, contact parameters, city of origin, and payment/booking modes.
- **Fleet Configurations**: Fleet vehicles are separated into:
  - *Private Listings*: Billed on a price-per-km rate, starting from the provider's base city.
  - *Fixed-fare Routes*: Operates scheduled trips between specific origins and destinations with fixed fares and departures.
- **Cab tab integration**: The traveler bookings hub searches active partner networks (`GET /api/provider/services`), listing matching route schedules and nearby private cabs.

### 5. Multi-seat Bookings with Passenger Form
- Includes passenger details forms allowing users to book multiple seats.
- Dynamic HTML forms prompt for the name and age of each individual passenger, which are saved in the database as serialized JSON and displayed to operators on their dispatch screens.

### 6. Live Navigation & Simulation Telemetry
- Supports a live telemetry dashboard where providers can flag "Start Trip" on active bookings.
- The system feeds simulated coordinate logs via Leaflet map markers, updating the traveler's UI in real time as the driver navigates.

### 7. Live Notification Badge & Dropdown
- A navbar notification dropdown polls live food orders and cab booking updates, displaying animated badge alerts and real-time status updates (e.g., *Driver Enroute*, *Preparing Meal*).

### 8. Mobile viewport Optimizations
- **Header Collapsing**: Hides text labels on navigation headers on mobile, presenting clean, click-friendly icons.
- **Horizontal Scrollable Tabs**: Booking filters scroll horizontally on touch devices.
- **Flexible Grid Stacking**: Multi-column grids (travel statistics, active listings, and booking registers) stack automatically to 1-column layouts.
- **Fullscreen Modal Drawers**: Modals like seat selectors and edit trip modals expand to cover full viewports on small screens.

---

## Project Structure

```
RoadBuddy/
├── backend/                             # Core FastAPI Backend API (Port 8000)
│   ├── app/
│   │   ├── main.py                      # FastAPI initialisation, routers, CORS and startup events
│   │   ├── core/                        # Config, database connections, JWT auth, and OTP utils
│   │   │   ├── auth.py                  # Rider and Provider authentication handlers
│   │   │   ├── config.py                # Environment configuration
│   │   │   └── database.py              # DB Engine & session generator
│   │   ├── models/
│   │   │   └── models.py                # Database declarations (SQLAlchemy models)
│   │   ├── schemas/
│   │   │   ├── schemas.py               # Pydantic schemas for core entities
│   │   │   └── booking_schemas.py       # Pydantic schemas for transit bookings
│   │   ├── provider/                    # Provider marketplace engine
│   │   │   ├── router.py                # Provider endpoints (Fleet CRUD, Setup, Notifications, telemetry)
│   │   │   └── schemas.py               # Pydantic schemas for provider operations
│   │   ├── routers/                     # Traveler JSON endpoints (trips, users, community, fuel, journals)
│   │   └── services/                    # AI business logic & calculators
│   ├── alembic/                         # Database schema migrations
│   ├── tests/                           # Pytest suite
│   ├── seed_data.py                     # Initial database seeding script
│   └── requirements.txt                 # Backend package requirements
├── frontend/                            # Standalone Jinja2 Presentation Web App (Port 3000)
│   ├── app/
│   │   ├── main.py                      # UI Server entry point & registrations
│   │   ├── core/
│   │   │   └── api_client.py            # Async HTTPX client interfacing with the backend API
│   │   ├── routers/                     # View controller routers (redirects, HTML rendering, proxies)
│   │   │   ├── auth.py                  # User/Traveler auth flow
│   │   │   ├── booking.py               # Bookings, Cab services search & Notifications
│   │   │   ├── provider.py              # Provider portals (Dashboard, Settings, Fleet setup, telemetry)
│   │   │   ├── trips.py                 # Plan trip pages & Pre-filled parameters
│   │   │   └── vehicles.py              # Rider garage controller
│   │   ├── templates/                   # Jinja2 views styled with Tailwind CSS
│   │   └── static/                      # Custom stylesheets and graphics (style.css, provider.css)
│   └── requirements.txt                 # Frontend package requirements
└── README.md                            # Comprehensive project guide
```

---

## Database Models

The schema uses SQLAlchemy to link entities:
- `User`: Traveler logins, vehicles list, active bookings.
- `Vehicle`: Personal vehicle specifications in traveler garages.
- `Provider`: Partner businesses, contacts, city, service profiles.
- `ProviderVehicleAsset`: Catalog items representing physical vehicles.
- `ProviderVehicle`: Active vehicle listings deployed for private hire or routes.
- `ProviderBooking`: Fleet reservations containing traveler schedules and JSON-serialized occupant rosters.
- `Trip` & `TripStop`: Saved itineraries and day plans.
- `CommunityRoute` & `RouteReview`: Public route-sharing hub entries.
- `Journal` & `JournalEntry`: Traveler expense sheets and daily diaries.
- `HotelBooking`, `TrainBooking`, `BusBooking`, `FlightBooking`: Core transit tickets.
- `Hotel`, `Train`, `Bus`, `Flight`: Seeded travel assets.
- `Restaurant`, `MenuItem`, `FoodOrder`, `FoodReview`: Partner dhabas and food catalog system.

---

## API Endpoints Matrix

| Router | Method | Path | Description | Authorization |
|---|---|---|---|---|
| **Users** | `POST` | `/api/users/register` | Register traveler | None |
| **Users** | `POST` | `/api/users/login` | Login traveler & fetch JWT | None |
| **Users** | `GET` | `/api/users/me` | Fetch traveler profile | Bearer Token |
| **Users** | `GET` | `/api/users/vehicles` | List traveler vehicles | Bearer Token |
| **Users** | `DELETE`| `/api/users/vehicles/{vehicle_id}` | Delete a personal vehicle | Bearer Token |
| **Trips** | `POST` | `/api/trips/generate` | Generate AI itinerary | Bearer Token |
| **Trips** | `POST` | `/api/trips/waypoints` | Fetch waypoint recommendations | None |
| **Trips** | `POST` | `/api/trips/safety-check` | Run AI route safety analysis | None |
| **Trips** | `POST` | `/api/trips/chat` | AI trip planning chat thread | None |
| **Fuel** | `POST` | `/api/fuel/calculate` | Calculate fuel & toll estimates | None |
| **Community**| `POST` | `/api/community/publish` | Publish a travel route | Bearer Token |
| **Community**| `GET` | `/api/community/search` | Natural-language route search | None |
| **Provider** | `POST` | `/api/provider/register` | Register a partner account | None |
| **Provider** | `POST` | `/api/provider/login` | Login partner & fetch JWT | None |
| **Provider** | `PATCH`| `/api/provider/me` | Update company config & alternate email | Provider Token |
| **Provider** | `GET` | `/api/provider/services` | Query available cab services | None |
| **Provider** | `GET` | `/api/provider/bookings/user`| Fetch unread alert states for travelers | Bearer Token |
| **Provider** | `POST` | `/api/provider/bookings/{id}/start-nav`| Start telemetry dispatch mapping | Provider Token |
| **Provider** | `POST` | `/api/provider/bookings/{id}/location`| Sync driver coordinates | Provider Token |
| **Food** | `GET` | `/api/food/restaurants` | Fetch seeded dhabas along cities | None |
| **Food** | `GET` | `/api/food/restaurants/{id}/menu` | List menu items | None |
| **Food** | `POST` | `/api/food/order` | Place prepaid meal order | Bearer Token |
| **Food** | `GET` | `/api/food/my-orders` | Fetch traveler order history | Bearer Token |

---

## Web Pages (Jinja2 Templates - Port 3000)

- **Traveler Dashboard & Planning**:
  - `/` : Landing explore page containing basic route searches.
  - `/login`, `/register`, `/verify-otp` : Authentication gates.
  - `/dashboard` : Widgets pane linking chatbots, recommendations, and routes.
  - `/plan-trip` : Route maps, waypoint recommendations, itinerary builders.
  - `/vehicles` : Vehicle garage (Add / Dynamic Remove).
  - `/bookings` : Bookings catalog supporting hotels, transit, and **cabs network search**.
  - `/my-bookings` : Traveler reservations drawer showing ticket details.
  - `/settings` : Profile edit forms.
  - `/start-trip` : Live maps HUD dashboard with cardinal compass tracking, HUD speed, and partner dhaba indicators.
- **Provider Dashboard Cockpit**:
  - `/provider/register`, `/provider/login` : Credentials validation.
  - `/provider/dashboard` : Live metrics, onboarding setup banners, revenue panels.
  - `/provider/vehicles` : Listing registers supporting route schedules and asset inventories.
  - `/provider/bookings` : Bookings manager with per-seat passenger list and live GPS coordinate sync.
  - `/provider/settings` : Partner company metadata updating.
  - `/food-provider/` : Onboarding setups, menu listings, order registers, and preparation timings for dhabas.

---

## Local Execution Guide

### 1. Launch the Backend API Service
1. Navigate to the backend directory:
   ```bash
   cd RoadBuddy/backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # On Windows
   # source venv/bin/activate   # On macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Setup environment variables by creating a `.env` file in the `backend/` folder:
   ```ini
   DATABASE_URL=sqlite:///./test.db
   SECRET_KEY=your-jwt-secret-key-here
   GROQ_API_KEY=your-groq-api-key-optional
   ```
5. Seed initial mock records (cabs, transit schedules, community routes, and **extensive Indian cities databases**):
   ```bash
   python seed_data.py
   ```
   *Note: This seeds 335 hotels, 502 trains, 502 buses, and 236 flights across 23 cities.*

6. Spin up the FastAPI API server:
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```

### 2. Launch the Frontend UI Web App [⏳ COMING SOON]
> [!NOTE]
> The frontend code is undergoing updates and is not fully prepared for public consumption/end-user execution yet. Once the updates are completed and the code is released, it can be executed as follows:
1. Navigate to the frontend directory:
   ```bash
   cd RoadBuddy/frontend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # On Windows
   # source venv/bin/activate   # On macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Spin up the Frontend server:
   ```bash
   uvicorn app.main:app --port 3000 --reload
   ```

### 3. Access URLs
- **Rider/Traveler App**: `⏳ Coming Soon (Undergoing Updates)`
- **Partner/Provider Portal**: `⏳ Coming Soon (Undergoing Updates)`
- **Interactive REST API Reference**: [http://localhost:8000/docs](http://localhost:8000/docs) (✅ Available)