# RoadBuddy 🚗
**AI-Powered Road Trip Planner for India**

RoadBuddy is a decoupled, modern web platform designed to help travellers in India plan and manage road trips end-to-end. It features AI-generated day-by-day itineraries, fuel and toll cost calculations, route safety assessments, community route sharing, personal trip journals with summaries, and an integrated travel marketplace supporting transit bookings (bus, train, flight, hotel) and a partner-run cab/vehicle provider fleet.

> [!IMPORTANT]
> **Frontend Code Status**: The standalone frontend web application is **Coming Soon** and has not been uploaded for public/end-user release yet. Currently, only the core backend API services (running on Port 8000) are fully operational and ready for use. You can interact with and test all features using the backend interactive API documentation (`/docs`).

---

## Architectural Overview

RoadBuddy is built as a split **decoupled microservices-like architecture** consisting of two standalone services communicating via asynchronous JSON REST APIs.

*Note: The frontend UI components described here are currently in development (**Coming Soon**) and are not yet uploaded for public use.*

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
| **Frontend UI Server** | FastAPI (Python) running on port 3000 | ⏳ **Coming Soon** (Not uploaded for use yet) |
| **Backend API Server** | FastAPI (Python) running on port 8000 | ✅ **Available & Fully Functional** |
| **Styling & Presentation** | Tailwind CSS + custom glassmorphic dark cockpit designs for providers | ⏳ **Coming Soon** |
| **Interactive Mapping** | Leaflet.js (OpenStreetMap + OSRM Routing Engines) | ⏳ **Coming Soon** |
| **Database & ORM** | SQLAlchemy ORM with Alembic migrations (SQLite for dev/testing, PostgreSQL for prod) | ✅ **Available** |
| **Authentication** | JWT (python-jose) + bcrypt hashing (isolated session cookies: `roadbuddy_token` for travelers, `provider_access_token` for partners) | ✅ **Available** |
| **AI Processing** | Groq API (Llama models) with local mock fallback configurations for offline development | ✅ **Available** |
| **Email Dispatch** | SMTP-based OTP code verification | ✅ **Available** |

---

## Core Features & Modules (Backend APIs Available)

### 1. AI-Powered Trip Planning
- **Itinerary Generator** (`POST /api/trips/generate`): Day-by-day plans specifying stops, estimated budgets, and travel tips tailored to season, group composition, and budget tier.
- **AI Waypoint Suggester**: Recommends scenic viewpoints, popular dhabas, and hidden attractions along the planned route.
- **AI Route Safety Checks**: Evaluates route safety profiles, flags terrain hazards, and assigns a safety score based on weather or seasonal conditions.
- **Conversational Chatbot**: An interactive chatbot helper residing in the dashboard for real-time travel planning suggestions.
- **AI Recommendations**: Personalized trip recommendations matching traveler interests.
- **AI Journal Summary**: Automatically summarizes daily logs and expenses into a structured story.

### 2. Intelligent Mapping & Routing (Telemetry & Map Backend Ready)
- Interactive Leaflet-based planner with reverse-geocoding coordinates capture.
- **Flexible UI Layout**: Prevents flexbox panel shrinkage during map interactions, supports collapsible search drawers, and provides a route summary overlay.
- Mobile layouts adapt to smaller screens by hiding text labels on icons and offering vertical layout stacks.

### 3. Traveler Garage & Vehicle Profiles
- Travelers can register personal vehicles to calculate fuel efficiency and custom ranges.
- **Dynamic Deletion**: Provides a vehicle deletion route `DELETE /api/users/vehicles/{vehicle_id}` allowing riders to remove cars directly from their garage dashboard using dynamic AJAX.

### 4. Cab Services & Provider Marketplace
A double-sided marketplace that links local travel operators and driver fleets with travelers:
- **Onboarding Setup**: Registered providers configure their company details, contact parameters, city of origin, and payment/booking modes.
- **Fleet Configurations**: Fleet vehicles are separated into:
  - *Private Listings*: Billed on a price-per-km rate, starting from the provider's base city.
  - *Fixed-fare Routes*: Operates scheduled trips between specific origins and destinations with fixed fares and departures.
- **Cab tab integration**: The traveler bookings hub searches active partner networks (`GET /api/provider/services`), listing matching route schedules and nearby private cabs.

### 5. Multi-seat Bookings with Passenger Form (Backend API Supported)
- Includes passenger details forms allowing users to book multiple seats.
- Dynamic HTML forms prompt for the name and age of each individual passenger, which are saved in the database as serialized JSON and displayed to operators on their dispatch screens.

### 6. Live Navigation & Simulation Telemetry
- Supports a live telemetry dashboard where providers can flag "Start Trip" on active bookings.
- The system feeds simulated coordinate logs via Leaflet map markers, updating the traveler's UI in real time as the driver navigates.

### 7. Notification Badges
- **Travelers**: A red notification dot appears in the dashboard header when a reservation's status changes. The dot is updated via background checks and marked as read automatically once the traveller loads `/my-bookings`.
- **Providers**: Displays red notification badges for new bookings, clearing them on view.

---

## Project Structure

```
RoadBuddy/
├── backend/                             # Core FastAPI Backend API (Port 8000) [AVAILABLE]
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
├── frontend/                            # Standalone Jinja2 Presentation Web App [COMING SOON / NOT UPLOADED]
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
│   │   └── static/                      # Custom stylesheets and graphics
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

---

## API Endpoints Matrix

| Router | Method | Path | Description | Authorization |
|---|---|---|---|---|
| **Users** | `POST` | `/api/users/register` | Register traveler | None |
| | `POST` | `/api/users/login` | Login traveler & fetch JWT | None |
| | `GET` | `/api/users/me` | Fetch traveler profile | Bearer Token |
| | `GET` | `/api/users/vehicles` | List traveler vehicles | Bearer Token |
| | `DELETE`| `/api/users/vehicles/{vehicle_id}` | Delete a personal vehicle | Bearer Token |
| **Trips** | `POST` | `/api/trips/generate` | Generate AI itinerary | Bearer Token |
| | `POST` | `/api/trips/waypoints` | Fetch waypoint recommendations | None |
| | `POST` | `/api/trips/safety-check` | Run AI route safety analysis | None |
| | `POST` | `/api/trips/chat` | AI trip planning chat thread | None |
| **Fuel** | `POST` | `/api/fuel/calculate` | Calculate fuel & toll estimates | None |
| **Community**| `POST` | `/api/community/publish` | Publish a travel route | Bearer Token |
| | `GET` | `/api/community/search` | Natural-language route search | None |
| **Provider** | `POST` | `/api/provider/register` | Register a partner account | None |
| | `POST` | `/api/provider/login` | Login partner & fetch JWT | None |
| | `PATCH`| `/api/provider/me` | Update company config & alternate email | Provider Token |
| | `GET` | `/api/provider/services` | Query available cab services | None |
| | `POST` | `/api/provider/bookings/mark-read`| Clear unread alerts for travelers | Bearer Token |
| | `POST` | `/api/provider/bookings/{id}/start-nav`| Start telemetry dispatch mapping | Provider Token |
| | `POST` | `/api/provider/bookings/{id}/location`| Sync driver coordinates | Provider Token |

---

## Web Pages (Jinja2 Templates - Port 3000) [⏳ COMING SOON]

*Note: All web pages and routes listed below are mock setups inside the frontend directory, slated for launch in the next release.*

- **Traveler Dashboard & Planning**:
  - `/` : Landing home containing basic route searches.
  - `/login`, `/register`, `/verify-otp` : Authentication gates.
  - `/dashboard` : Widgets pane linking chatbots, recommendations, and routes.
  - `/plan-trip` : Route maps, waypoint recommendations, itinerary builders.
  - `/vehicles` : Vehicle garage (Add / Dynamic Remove).
  - `/bookings` : Bookings catalog supporting hotels, transit, and **cabs network search**.
  - `/my-bookings` : Traveler reservations drawer showing ticket details.
  - `/settings` : Profile edit forms.
- **Provider Dashboard Cockpit**:
  - `/provider/register`, `/provider/login` : Credentials validation.
  - `/provider/dashboard` : Live metrics, onboarding setup banners, revenue panels.
  - `/provider/vehicles` : Listing registers supporting route schedules and asset inventories.
  - `/provider/bookings` : Bookings manager with per-seat passenger list and live GPS coordinate sync.
  - `/provider/settings` : Partner company metadata updating.

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
5. Seed initial mock records (cabs, transit schedules, community routes):
   ```bash
   python seed_data.py
   ```
6. Spin up the FastAPI API server:
   ```bash
   uvicorn app.main:app --port 8000 --reload
   ```

### 2. Launch the Standalone Frontend Web App [⏳ COMING SOON / IN DEV]
> [!NOTE]
> The frontend code is not fully prepared for public consumption/end-user execution yet. Once the code is uploaded and released, it can be executed as follows:
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
- **Rider/Traveler App**: `http://localhost:3000` (⏳ Coming Soon)
- **Partner/Provider Portal**: `http://localhost:3000/provider/login` (⏳ Coming Soon)
- **Interactive REST API Reference**: [http://localhost:8000/docs](http://localhost:8000/docs) (✅ Available)

---

## Known Gaps & Future Roadmap

1. **Mapping Provider Upgrade**: Swap OSRM and OpenStreetMap for Google Maps/Routing APIs to enable traffic routing and turn-by-turn alerts.
2. **Real-time Payment Integration**: Setup Razorpay or UPI gateways on booking confirmation.
3. **True Web Sockets**: Replace long-polling loops with true WebSockets for instant coordinate syncing and notification alerts.
4. **Transit APIs Integration**: Connect flight, bus, train and hotel searches with live flight trackers or booking aggregators.