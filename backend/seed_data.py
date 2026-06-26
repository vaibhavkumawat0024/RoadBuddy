"""
Seed Data Script — RoadBuddy
-------------------------------
Generates and seeds 100 hotels, 100 trains, 100 buses, and 100 flights in the database.
Run this once: python seed_data.py
"""

import random
from app.core.database import SessionLocal, Base, engine
from app.models.models import Hotel, Train, Bus, Flight

CITIES = ["Delhi", "Mumbai", "Jaipur", "Udaipur", "Goa", "Manali", "Jodhpur", "Agra", "Shimla", "Bangalore", "Kolkata", "Pune", "Chennai", "Hyderabad"]

# Explicit popular routes to guarantee search results
POPULAR_ROUTES = [
    ("Jaipur", "Udaipur"),
    ("Udaipur", "Jaipur"),
    ("Jaipur", "Delhi"),
    ("Delhi", "Jaipur"),
    ("Delhi", "Manali"),
    ("Manali", "Delhi"),
    ("Mumbai", "Goa"),
    ("Goa", "Mumbai")
]

# ── Generating 100 Hotels ─────────────────────────────────────────────────────
def generate_hotels():
    hotel_names = ["Taj", "Oberoi", "Zostel", "OYO Townhouse", "Lemon Tree", "Ginger", "Radisson", "Marriott", "Hyatt", "FabHotel", "Treebo", "Grand Vista"]
    hotel_types = ["Palace", "Resort", "Inn", "Hostel", "Hotel", "Suites", "Homestay", "Heritage"]
    hotel_amenities = ["WiFi, AC", "WiFi, AC, Pool", "WiFi, Dorm, Common Area", "WiFi, AC, Restaurant", "WiFi, AC, Restaurant, Pool, Gym", "WiFi, AC, Spa, Pool, Gym"]

    hotels = []
    for i in range(100):
        city = random.choice(CITIES)
        name = f"{random.choice(hotel_names)} {random.choice(hotel_types)} {i+1}"
        address = f"Street {random.randint(1, 20)}, near Mall Road, {city}"
        star_rating = round(random.uniform(3.0, 5.0), 1)
        price_per_night = random.randint(800, 15000)
        total_rooms = random.randint(15, 50)
        amenities = random.choice(hotel_amenities)
        hotels.append(Hotel(
            name=name, city=city, address=address, star_rating=star_rating,
            price_per_night_inr=price_per_night, total_rooms=total_rooms,
            rooms_booked=0, amenities=amenities, image_url=None
        ))
    return hotels

# ── Generating 100 Trains ─────────────────────────────────────────────────────
def generate_trains():
    train_types = ["Shatabdi Express", "Rajdhani Express", "Vande Bharat", "Duronto Express", "Garib Rath", "Intercity Express", "Express", "Mail"]
    train_names = ["Pink City", "Mewar", "Chetak", "Golden Temple", "Paschim", "Ashram", "Karnavati", "Deccan Queen"]

    trains = []
    # First seed popular routes to guarantee matches
    for i, (orig, dest) in enumerate(POPULAR_ROUTES * 3): # 24 trains
        t_type = random.choice(train_types)
        t_name = f"{random.choice(train_names)} {t_type}"
        t_num = f"{12000 + i}"
        dep_time = f"{6 + i % 16:02d}:{random.choice([0, 15, 30, 45]):02d}"
        dur = round(random.uniform(3.5, 9.0), 1)
        arr_h = int((int(dep_time.split(":")[0]) + int(dur)) % 24)
        arr_m = int((int(dep_time.split(":")[1]) + (dur % 1)*60) % 60)
        arr_time = f"{arr_h:02d}:{arr_m:02d}"
        fare = random.randint(350, 1800)
        travel_class = random.choice(["Sleeper", "AC3", "AC2", "AC1"])
        trains.append(Train(
            train_name=t_name, train_number=t_num, origin=orig, destination=dest,
            departure_time=dep_time, arrival_time=arr_time, duration_hrs=dur,
            fare_inr=fare, total_seats=100, seats_booked=0, travel_class=travel_class
        ))

    # Seed remaining randomly to reach 100
    for i in range(100 - len(trains)):
        orig = random.choice(CITIES)
        dest = random.choice([c for c in CITIES if c != orig])
        t_type = random.choice(train_types)
        t_name = f"{random.choice(train_names)} {t_type}"
        t_num = f"{13000 + i}"
        dep_time = f"{random.randint(0, 23):02d}:{random.choice([0, 15, 30, 45]):02d}"
        dur = round(random.uniform(2.0, 18.0), 1)
        arr_h = int((int(dep_time.split(":")[0]) + int(dur)) % 24)
        arr_m = int((int(dep_time.split(":")[1]) + (dur % 1)*60) % 60)
        arr_time = f"{arr_h:02d}:{arr_m:02d}"
        fare = random.randint(250, 2500)
        travel_class = random.choice(["Sleeper", "AC3", "AC2", "AC1"])
        trains.append(Train(
            train_name=t_name, train_number=t_num, origin=orig, destination=dest,
            departure_time=dep_time, arrival_time=arr_time, duration_hrs=dur,
            fare_inr=fare, total_seats=120, seats_booked=0, travel_class=travel_class
        ))
    return trains

# ── Generating 100 Buses ──────────────────────────────────────────────────────
def generate_buses():
    bus_operators = ["RSRTC Volvo", "Gujarat Travels", "Orange Travels", "SRS Travels", "VRL Travels", "Intrcity SmartBus", "Zingbus", "Shrinath Travels", "Neeta Travels"]
    bus_types = ["AC Seater", "AC Sleeper", "Non-AC Seater", "Non-AC Sleeper", "Multi-Axle Volvo AC"]

    buses = []
    # First seed popular routes to guarantee matches
    for i, (orig, dest) in enumerate(POPULAR_ROUTES * 3): # 24 buses
        operator = random.choice(bus_operators)
        b_type = random.choice(bus_types)
        dep_time = f"{6 + i % 16:02d}:{random.choice([0, 15, 30, 45]):02d}"
        dur = round(random.uniform(4.0, 10.0), 1)
        arr_h = int((int(dep_time.split(":")[0]) + int(dur)) % 24)
        arr_m = int((int(dep_time.split(":")[1]) + (dur % 1)*60) % 60)
        arr_time = f"{arr_h:02d}:{arr_m:02d}"
        fare = random.randint(300, 1500)
        buses.append(Bus(
            operator_name=f"{operator} {i+1}", bus_type=b_type, origin=orig, destination=dest,
            departure_time=dep_time, arrival_time=arr_time, duration_hrs=dur,
            fare_inr=fare, total_seats=40, seats_booked=0
        ))

    # Seed remaining randomly to reach 100
    for i in range(100 - len(buses)):
        orig = random.choice(CITIES)
        dest = random.choice([c for c in CITIES if c != orig])
        operator = random.choice(bus_operators)
        b_type = random.choice(bus_types)
        dep_time = f"{random.randint(0, 23):02d}:{random.choice([0, 15, 30, 45]):02d}"
        dur = round(random.uniform(3.0, 12.0), 1)
        arr_h = int((int(dep_time.split(":")[0]) + int(dur)) % 24)
        arr_m = int((int(dep_time.split(":")[1]) + (dur % 1)*60) % 60)
        arr_time = f"{arr_h:02d}:{arr_m:02d}"
        fare = random.randint(200, 1800)
        buses.append(Bus(
            operator_name=f"{operator} {i+25}", bus_type=b_type, origin=orig, destination=dest,
            departure_time=dep_time, arrival_time=arr_time, duration_hrs=dur,
            fare_inr=fare, total_seats=42, seats_booked=0
        ))
    return buses

# ── Generating 100 Flights ────────────────────────────────────────────────────
def generate_flights():
    airlines = ["IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air", "Air India Express"]
    flight_classes = ["Economy", "Premium Economy", "Business"]

    flights = []
    # First seed popular routes to guarantee matches (excluding Manali since it has no commercial flight airport in major CITIES)
    FLIGHT_POPULAR_ROUTES = [
        ("Jaipur", "Delhi"),
        ("Delhi", "Jaipur"),
        ("Mumbai", "Goa"),
        ("Goa", "Mumbai"),
        ("Delhi", "Mumbai"),
        ("Mumbai", "Delhi"),
        ("Delhi", "Goa"),
        ("Goa", "Delhi")
    ]

    for i, (orig, dest) in enumerate(FLIGHT_POPULAR_ROUTES * 3): # 24 flights
        airline = random.choice(airlines)
        fl_num = f"{airline[:2].upper()}-{200 + i}"
        dep_time = f"{6 + i % 16:02d}:{random.choice([0, 15, 30, 45]):02d}"
        dur = round(random.uniform(1.0, 2.5), 1)
        arr_h = int((int(dep_time.split(":")[0]) + int(dur)) % 24)
        arr_m = int((int(dep_time.split(":")[1]) + (dur % 1)*60) % 60)
        arr_time = f"{arr_h:02d}:{arr_m:02d}"
        fare = random.randint(3000, 8500)
        travel_class = random.choice(flight_classes)
        flights.append(Flight(
            airline=airline, flight_number=fl_num, origin=orig, destination=dest,
            departure_time=dep_time, arrival_time=arr_time, duration_hrs=dur,
            fare_inr=fare, total_seats=180, seats_booked=0, travel_class=travel_class
        ))

    # Seed remaining randomly to reach 100
    for i in range(100 - len(flights)):
        orig = random.choice(CITIES)
        dest = random.choice([c for c in CITIES if c != orig])
        airline = random.choice(airlines)
        fl_num = f"{airline[:2].upper()}-{300 + i}"
        dep_time = f"{random.randint(0, 23):02d}:{random.choice([0, 15, 30, 45]):02d}"
        dur = round(random.uniform(1.0, 4.0), 1)
        arr_h = int((int(dep_time.split(":")[0]) + int(dur)) % 24)
        arr_m = int((int(dep_time.split(":")[1]) + (dur % 1)*60) % 60)
        arr_time = f"{arr_h:02d}:{arr_m:02d}"
        fare = random.randint(2500, 12000)
        travel_class = random.choice(flight_classes)
        flights.append(Flight(
            airline=airline, flight_number=fl_num, origin=orig, destination=dest,
            departure_time=dep_time, arrival_time=arr_time, duration_hrs=dur,
            fare_inr=fare, total_seats=150, seats_booked=0, travel_class=travel_class
        ))
    return flights


def seed():
    # Automatically create tables in SQLite database if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        has_hotels = db.query(Hotel).first() is not None
        has_trains = db.query(Train).first() is not None
        has_buses = db.query(Bus).first() is not None
        has_flights = db.query(Flight).first() is not None

        if has_hotels or has_trains or has_buses or has_flights:
            print("Database already contains seeded data. Skipping.")
            return

        hotels = generate_hotels()
        trains = generate_trains()
        buses = generate_buses()
        flights = generate_flights()

        db.add_all(hotels)
        db.add_all(trains)
        db.add_all(buses)
        db.add_all(flights)
        db.commit()
        print(f"[SUCCESS] Seeded {len(hotels)} hotels, {len(trains)} trains, {len(buses)} buses, {len(flights)} flights!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
