# RoadBuddy — Complete Project Report
**AI-Powered Road Trip Planner | Web Application**
**Date: June 2026 | Built by: Mahendra & Kunal**

---

## 1. Project Overview

RoadBuddy is a full-stack AI-powered road trip planning web application built for Indian travellers. It helps users plan road trips, estimate costs, discover hidden gems, check route safety, and book transport and hotels — all in one place.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL (Neon Cloud) |
| AI | Groq API (Llama 3 — free) |
| Auth | JWT (JSON Web Tokens) |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Frontend | HTML + CSS + Vanilla JS (Jinja2 templates) |
| Deployment | Render (backend) |
| Version Control | GitHub |

---

## 3. Database Models (6 Tables)

| Model | Description |
|---|---|
| User | Stores user accounts with hashed passwords |
| Vehicle | User's vehicles with fuel type and mileage |
| Trip | Planned trips with full cost breakdown |
| TripStop | Individual stops for each trip |
| CommunityRoute | Publicly shared routes |
| RouteReview | Reviews and ratings for community routes |
| Journal | Trip journals with daily entries |
| JournalEntry | Individual journal entries with expenses |
| Booking | Transport bookings (bus/train/flight) |
| TransportOption | Available transport options |

---

## 4. API Endpoints (40+)

### Users
- POST /api/users/register
- POST /api/users/login
- POST /api/users/refresh
- GET /api/users/me
- POST /api/users/logout

### Trips
- POST /api/trips/generate — AI itinerary generation
- GET /api/trips/my — List user trips
- GET /api/trips/{id} — Get trip details
- GET /api/trips/{id}/cost — Cost breakdown
- DELETE /api/trips/{id} — Delete trip
- POST /api/trips/suggest-waypoints — AI waypoint suggestions
- POST /api/trips/chat — AI trip chatbot
- POST /api/trips/safety-check — AI route safety
- POST /api/trips/recommendations — AI trip recommendations

### Fuel
- POST /api/fuel/estimate
- GET /api/fuel/prices
- GET /api/fuel/tolls
- POST /api/fuel/compare
- GET /api/fuel/history

### Community
- GET /api/community/routes
- POST /api/community/routes
- GET /api/community/routes/{id}
- POST /api/community/routes/{id}/review
- POST /api/community/routes/{id}/save
- POST /api/community/routes/{id}/clone
- GET /api/community/routes/trending
- POST /api/community/smart-search — AI smart search

### Journal
- POST /api/journal
- GET /api/journal/trip/{id}
- PUT /api/journal/{id}
- DELETE /api/journal/{id}
- POST /api/journal/expenses
- GET /api/journal/expenses/trip/{id}
- POST /api/journal/summarize — AI journal summarizer

### Transport
- GET /api/transport/search
- POST /api/transport/book

---

## 5. AI Features (7 Total)

| Feature | Endpoint | Description |
|---|---|---|
| AI Trip Planner | POST /api/trips/generate | Generates full day-by-day itinerary with stops, costs, hotels, food |
| AI Waypoint Suggestions | POST /api/trips/suggest-waypoints | Suggests hidden gems, dhabas, viewpoints between two cities |
| AI Trip Chatbot | POST /api/trips/chat | Multi-turn conversational trip planning assistant |
| AI Journal Summarizer | POST /api/journal/summarize | Turns daily journal entries into a beautiful trip story |
| AI Route Safety Analyzer | POST /api/trips/safety-check | Flags hazards, gives safety score, seasonal warnings |
| AI Smart Search | POST /api/community/smart-search | Natural language search — "beach trip under 5000 for couple" |
| AI Trip Recommendations | POST /api/trips/recommendations | 5 personalized trip suggestions based on preferences |

All AI features powered by **Groq API (Llama 3)** — free and fast.

---

## 6. Web Pages

| Page | URL | Description |
|---|---|---|
| Register | /register | Create new account |
| OTP Verify | /verify-otp | Verify with OTP (default: 1234) |
| Login | /login | Login with email/password |
| Dashboard | /dashboard | Main dashboard with all 6 AI feature widgets |
| Plan Trip | /plan-trip | 4-step trip planner with AI itinerary + safety + map + bookings |
| My Trips | /my-trips | View all saved trips with stops and cost breakdown |
| My Vehicles | /add-vehicle | Add and manage vehicles |
| Community | /community | Browse and search community routes |
| Profile | /profile | View and update profile |

---

## 7. Key Features

### Trip Planning
- AI generates complete day-by-day itinerary
- Real Indian highway numbers (NH-48, NH-8 etc.)
- Season-aware recommendations (summer/monsoon/winter)
- Group-type specific stops (family/couple/friends/solo)
- Budget breakdown per category

### Maps & Booking
- Google Maps route embed
- Train booking → IRCTC, Ixigo
- Bus booking → RedBus, Ixigo
- Flight booking → Google Flights, MakeMyTrip, EaseMyTrip
- Hotel booking → Booking.com, MakeMyTrip, OYO, Airbnb
- Toll calculator → NHAI
- Fuel prices → Google Search

### Safety
- AI analyzes route hazards
- Safety score out of 10
- Seasonal warnings (flood, fog, landslide)
- Emergency contact numbers (1033, 108, 1073)

### Community
- Publish and discover routes
- Rate and review routes
- Clone routes as personal trips
- AI smart search in natural language

---

## 8. Authentication Flow

```
Register → OTP (1234) → Login → JWT Cookie → Dashboard
```

- Passwords hashed with bcrypt
- JWT tokens stored in httponly cookies
- Token expiry: 24 hours

---

## 9. Deployment

| Service | Platform | URL |
|---|---|---|
| Backend API | Render (free) | https://roadbuddy-backend.onrender.com |
| Database | Neon PostgreSQL (free) | Cloud hosted |
| Code | GitHub | https://github.com/Kunal14695/RoadBuddy |

---

## 10. Environment Variables

```
DATABASE_URL    = Neon PostgreSQL connection string
GROQ_API_KEY    = Groq API key for AI features
SECRET_KEY      = JWT signing secret
ANTHROPIC_API_KEY = (optional, not used)
GEMINI_API_KEY  = (optional, not used)
GOOGLE_MAPS_API_KEY = (optional, for real routing)
```

---

## 11. Work Division

### Mahendra (AI & Frontend)
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

### Kunal (Backend & Database)
- FastAPI project setup and structure
- JWT authentication with bcrypt
- User registration and login
- Vehicle management API
- Fuel and toll calculator
- Transport booking (bus/train/flight)
- Neon PostgreSQL setup
- All 6 database tables
- 33 automated tests
- Community routes module
- Trip journal module
- Alembic migrations
- Render deployment
- HTML templates (base, login, register, verify_otp, dashboard)

---

## 12. What's Remaining (Future Work)

| Feature | Status | Notes |
|---|---|---|
| Real Google Maps API | Pending | Needs paid API key |
| Real IRCTC/RedBus API | Pending | Needs partnership/paid access |
| Real fuel price API | Pending | Indian Oil API |
| Real toll API | Pending | NHAI API |
| Push notifications | Pending | Firebase |
| Photo uploads | Pending | S3/Cloudinary |
| Email OTP | Pending | Replace hardcoded 1234 |
| React Native app | Not planned | Web app instead |
| Payment integration | Future | Razorpay |

---

## 13. How to Run Locally

```bash
# Clone repo
git clone https://github.com/Kunal14695/RoadBuddy.git
cd RoadBuddy/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Fill in DATABASE_URL and GROQ_API_KEY

# Run server
uvicorn app.main:app --reload

# Open browser
http://localhost:8000/dashboard
http://localhost:8000/docs
```

---

*RoadBuddy — Plan smarter, travel better 🚗*
