from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.provider.router import router as provider_router
from fastapi.middleware.cors import CORSMiddleware
from app.provider.pages import router as provider_pages_router
from app.routers import booking

from app.routers import trips, fuel, users, community, journal, transport
from app.pages import auth_pages, dashboard_pages
from app.core.database import engine
from sqlalchemy import text
from app.core.config import settings

app = FastAPI(
    title="RoadBuddy AI",
    description="India's Ultimate Road Trip Companion — API Backend",
    version="1.0.0",
)

# Run schema updates on startup
@app.on_event("startup")
async def run_migrations():
    with engine.begin() as connection:
        try:
            connection.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS alternate_email VARCHAR;"))
            connection.execute(text("ALTER TABLE providers ADD COLUMN IF NOT EXISTS booking_mode VARCHAR;"))
            connection.execute(text("ALTER TABLE provider_vehicles ADD COLUMN IF NOT EXISTS arrival_time VARCHAR;"))
        except Exception as e:
            print("Schema update error:", e)



# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(users.router,     prefix="/api/users",     tags=["Users & Auth"])
app.include_router(trips.router,     prefix="/api/trips",     tags=["AI Trip Planner"])
app.include_router(fuel.router,      prefix="/api/fuel",      tags=["Fuel & Toll"])
app.include_router(community.router, prefix="/api/community", tags=["Community Routes"])
app.include_router(journal.router,   prefix="/api/journal",   tags=["Trip Journal"])
app.include_router(transport.router, prefix="/api/transport", tags=["Transport"])
app.include_router(provider_router, prefix="/api/provider", tags=["Provider"])
app.include_router(provider_pages_router)
app.include_router(booking.router, prefix="/api/booking", tags=["Booking"])

# UI page routes
app.include_router(auth_pages.router)
app.include_router(dashboard_pages.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "RoadBuddy AI backend is running 🚗", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
