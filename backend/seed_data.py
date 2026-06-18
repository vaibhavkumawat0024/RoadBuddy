"""
Seed Data Script — RoadBuddy
-------------------------------
Adds sample hotels, trains, buses, and flights to the database.
Run this once: python seed_data.py
Save as: backend/seed_data.py
"""

from app.core.database import SessionLocal
from app.models.models import Hotel, Train, Bus, Flight



# ── Hotels ─────────────────────────────────────────────────────────────────

hotels = [
    Hotel(name="Hotel Pearl Palace", city="Jaipur", address="Hari Kishan Somani Marg, Jaipur",
          star_rating=4.0, price_per_night_inr=2200, total_rooms=20,
          amenities="WiFi, AC, Restaurant, Pool", image_url=None),
    Hotel(name="Trident Jaipur", city="Jaipur", address="Amber Fort Road, Jaipur",
          star_rating=4.5, price_per_night_inr=5500, total_rooms=15,
          amenities="WiFi, AC, Spa, Pool, Gym", image_url=None),
    Hotel(name="Zostel Jaipur", city="Jaipur", address="Ajmer Road, Jaipur",
          star_rating=3.5, price_per_night_inr=900, total_rooms=30,
          amenities="WiFi, Dorm, Common Area", image_url=None),

    Hotel(name="Hotel Lake Pichola", city="Udaipur", address="Lake Pichola, Udaipur",
          star_rating=4.2, price_per_night_inr=3200, total_rooms=18,
          amenities="WiFi, AC, Lake View, Restaurant", image_url=None),
    Hotel(name="Taj Lake Palace", city="Udaipur", address="Lake Pichola, Udaipur",
          star_rating=5.0, price_per_night_inr=18000, total_rooms=10,
          amenities="WiFi, AC, Spa, Pool, Lake View, Butler", image_url=None),
    Hotel(name="OYO Udaipur Inn", city="Udaipur", address="City Palace Road, Udaipur",
          star_rating=3.0, price_per_night_inr=1100, total_rooms=25,
          amenities="WiFi, AC, Parking", image_url=None),

    Hotel(name="The Himalayan Resort", city="Manali", address="Old Manali Road",
          star_rating=4.3, price_per_night_inr=4200, total_rooms=12,
          amenities="WiFi, Bonfire, Mountain View, Restaurant", image_url=None),
    Hotel(name="Zostel Manali", city="Manali", address="Old Manali",
          star_rating=3.8, price_per_night_inr=1000, total_rooms=22,
          amenities="WiFi, Dorm, Cafe, Bonfire", image_url=None),

    Hotel(name="Taj Exotica Goa", city="Goa", address="Benaulim Beach, Goa",
          star_rating=5.0, price_per_night_inr=15000, total_rooms=14,
          amenities="WiFi, Beach Access, Spa, Pool", image_url=None),
    Hotel(name="Goa Beach Hostel", city="Goa", address="Anjuna Beach, Goa",
          star_rating=3.5, price_per_night_inr=800, total_rooms=28,
          amenities="WiFi, Beach Access, Bar", image_url=None),
]

# ── Trains ─────────────────────────────────────────────────────────────────

trains = [
    Train(train_name="Pink City Express", train_number="12986", origin="Jaipur", destination="Udaipur",
          departure_time="06:00", arrival_time="13:30", duration_hrs=7.5, fare_inr=450,
          total_seats=120, travel_class="Sleeper"),
    Train(train_name="Udaipur AC Express", train_number="19666", origin="Jaipur", destination="Udaipur",
          departure_time="22:00", arrival_time="05:30", duration_hrs=7.5, fare_inr=1200,
          total_seats=80, travel_class="AC3"),

    Train(train_name="Jaipur Delhi Shatabdi", train_number="12016", origin="Jaipur", destination="Delhi",
          departure_time="05:50", arrival_time="10:40", duration_hrs=4.8, fare_inr=900,
          total_seats=100, travel_class="AC2"),
    Train(train_name="Ajmer Shatabdi", train_number="12015", origin="Delhi", destination="Jaipur",
          departure_time="06:05", arrival_time="11:00", duration_hrs=4.9, fare_inr=950,
          total_seats=100, travel_class="AC2"),

    Train(train_name="Goa Express", train_number="12780", origin="Jaipur", destination="Goa",
          departure_time="14:20", arrival_time="16:00", duration_hrs=25.7, fare_inr=1800,
          total_seats=90, travel_class="Sleeper"),
]

# ── Buses ──────────────────────────────────────────────────────────────────

buses = [
    Bus(operator_name="RSRTC Volvo", bus_type="AC Seater", origin="Jaipur", destination="Udaipur",
        departure_time="07:00", arrival_time="14:00", duration_hrs=7.0, fare_inr=650,
        total_seats=40),
    Bus(operator_name="Shrinath Travels", bus_type="AC Sleeper", origin="Jaipur", destination="Udaipur",
        departure_time="22:30", arrival_time="05:30", duration_hrs=7.0, fare_inr=900,
        total_seats=36),

    Bus(operator_name="Zingbus", bus_type="AC Sleeper", origin="Jaipur", destination="Manali",
        departure_time="18:00", arrival_time="08:00", duration_hrs=14.0, fare_inr=1500,
        total_seats=30),
    Bus(operator_name="HRTC Volvo", bus_type="AC Seater", origin="Delhi", destination="Manali",
        departure_time="20:00", arrival_time="08:00", duration_hrs=12.0, fare_inr=1200,
        total_seats=42),

    Bus(operator_name="Paulo Travels", bus_type="AC Sleeper", origin="Jaipur", destination="Goa",
        departure_time="16:00", arrival_time="14:00", duration_hrs=22.0, fare_inr=2200,
        total_seats=32),
]

# ── Flights ────────────────────────────────────────────────────────────────

flights = [
    Flight(airline="IndiGo", flight_number="6E-2341", origin="Jaipur", destination="Udaipur",
           departure_time="09:15", arrival_time="10:10", duration_hrs=0.9, fare_inr=3200,
           total_seats=180, travel_class="Economy"),
    Flight(airline="Air India", flight_number="AI-9847", origin="Jaipur", destination="Delhi",
           departure_time="11:30", arrival_time="12:35", duration_hrs=1.1, fare_inr=2800,
           total_seats=150, travel_class="Economy"),
    Flight(airline="IndiGo", flight_number="6E-5612", origin="Delhi", destination="Manali",
           departure_time="07:45", arrival_time="08:50", duration_hrs=1.1, fare_inr=4500,
           total_seats=180, travel_class="Economy"),
    Flight(airline="SpiceJet", flight_number="SG-8123", origin="Jaipur", destination="Goa",
           departure_time="13:20", arrival_time="15:40", duration_hrs=2.3, fare_inr=5200,
           total_seats=189, travel_class="Economy"),
    Flight(airline="Vistara", flight_number="UK-945", origin="Mumbai", destination="Goa",
           departure_time="08:00", arrival_time="09:10", duration_hrs=1.2, fare_inr=3800,
           total_seats=160, travel_class="Economy"),
]


def seed():
    db = SessionLocal()
    try:
        has_hotels = db.query(Hotel).first() is not None
        has_trains = db.query(Train).first() is not None
        has_buses = db.query(Bus).first() is not None
        has_flights = db.query(Flight).first() is not None

        if has_hotels or has_trains or has_buses or has_flights:
            print("Database already contains seeded data. Skipping.")
            return

        db.add_all(hotels)
        db.add_all(trains)
        db.add_all(buses)
        db.add_all(flights)
        db.commit()
        print(f"✅ Seeded {len(hotels)} hotels, {len(trains)} trains, {len(buses)} buses, {len(flights)} flights!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
