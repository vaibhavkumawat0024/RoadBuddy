import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.schemas import TripCreate, TravelMode, GroupType
from app.services.ai_planner import generate_itinerary

async def main():
    trip_create = TripCreate(
        origin="Jaipur",
        destination="Manali",
        origin_lat=26.9124,
        origin_lon=75.7873,
        destination_lat=32.2396,
        destination_lon=77.1887,
        start_date="2026-07-04",
        end_date="2026-07-09",
        budget_inr=24000.0,
        travel_mode=TravelMode.cab_service,
        group_type=GroupType.solo,
        num_people=1
    )
    vehicle_info = {
        "fuel_type": "petrol",
        "category": "car",
        "mileage_kmpl": 15.0
    }
    
    print("Generating itinerary...")
    try:
        trip_out = await generate_itinerary(trip_create, vehicle_info)
        print("Success!")
        print("Stops generated:", len(trip_out.stops))
        for stop in trip_out.stops[:5]:
            print(f"Day {stop.day} {stop.time_slot}: {stop.place_name} - {stop.place_type}")
    except Exception as e:
        print("Failed with error:", e)

if __name__ == "__main__":
    asyncio.run(main())
