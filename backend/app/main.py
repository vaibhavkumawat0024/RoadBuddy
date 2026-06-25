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
    statements = [
        "ALTER TABLE providers ADD COLUMN IF NOT EXISTS alternate_email VARCHAR;",
        "ALTER TABLE providers ADD COLUMN IF NOT EXISTS booking_mode VARCHAR;",
        "ALTER TABLE provider_vehicles ADD COLUMN IF NOT EXISTS arrival_time VARCHAR;",
        "ALTER TABLE provider_vehicles ADD COLUMN IF NOT EXISTS pickup_points VARCHAR;",
        "ALTER TABLE provider_vehicles ADD COLUMN IF NOT EXISTS dropoff_points VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS dropoff_location VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS selected_seats VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS passenger_phone VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS passenger_email VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS navigation_status VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS driver_lat FLOAT;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS driver_lon FLOAT;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS message_unread BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE provider_vehicles ADD COLUMN IF NOT EXISTS service_dates VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS passenger_details VARCHAR;",
        "ALTER TABLE provider_bookings ADD COLUMN IF NOT EXISTS provider_unread BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE trips ADD COLUMN IF NOT EXISTS end_date VARCHAR;",
        "ALTER TABLE trips ADD COLUMN IF NOT EXISTS group_type VARCHAR;",
        "ALTER TABLE trips ADD COLUMN IF NOT EXISTS num_people INTEGER DEFAULT 1;",
        "ALTER TABLE trips ADD COLUMN IF NOT EXISTS origin_lat FLOAT;",
        "ALTER TABLE trips ADD COLUMN IF NOT EXISTS origin_lon FLOAT;",
        "ALTER TABLE trips ADD COLUMN IF NOT EXISTS destination_lat FLOAT;",
        "ALTER TABLE trips ADD COLUMN IF NOT EXISTS destination_lon FLOAT;"
    ]
    with engine.begin() as connection:
        dialect = connection.dialect.name
        if dialect == "sqlite":
            create_assets_table = """
            CREATE TABLE IF NOT EXISTS provider_vehicle_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                vehicle_type VARCHAR NOT NULL,
                vehicle_name VARCHAR NOT NULL,
                driver_included BOOLEAN DEFAULT 1,
                total_seats INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(provider_id) REFERENCES providers(id)
            );
            """
        else:
            create_assets_table = """
            CREATE TABLE IF NOT EXISTS provider_vehicle_assets (
                id SERIAL PRIMARY KEY,
                provider_id INTEGER NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
                vehicle_type VARCHAR NOT NULL,
                vehicle_name VARCHAR NOT NULL,
                driver_included BOOLEAN DEFAULT TRUE,
                total_seats INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        try:
            connection.execute(text(create_assets_table))
        except Exception as e:
            print(f"Failed to create provider_vehicle_assets table: {e}")

        for stmt in statements:
            try:
                connection.execute(text(stmt))
            except Exception as e:
                print(f"Schema update statement skipped: {stmt}. Reason: {e}")

        try:
            connection.execute(text("ALTER TABLE provider_vehicles ADD COLUMN IF NOT EXISTS vehicle_asset_id INTEGER;"))
        except Exception as e:
            print(f"Failed to add vehicle_asset_id to provider_vehicles: {e}")




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
    # Trigger uvicorn reload to pick up new env variables
    return {"status": "ok"}
