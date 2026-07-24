"""
AI Trip Planner Service — RoadBuddy v2 (Groq)
----------------------------------------------
Powered by Groq API (free) with Llama 3 model.
"""

import json
import httpx
from datetime import date
from app.core.config import settings
from app.schemas.schemas import TripCreate, ItineraryStop, TripOut, TravelMode

GROQ_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GROQ_MODEL = "gemini-1.5-flash"


def get_season(start_date) -> str:
    try:
        if isinstance(start_date, str):
            month = int(start_date.split("-")[1])
        else:
            month = start_date.month
    except Exception:
        month = date.today().month
    if month in [3, 4, 5]:
        return "summer"
    elif month in [6, 7, 8, 9]:
        return "monsoon"
    else:
        return "winter"


def get_season_tips(season: str, destination: str) -> str:
    if season == "summer":
        return f"It is SUMMER. Advise travelling early morning before 9am. Carry extra water. Avoid 12pm-4pm driving."
    elif season == "monsoon":
        return f"It is MONSOON. Warn about slippery roads near {destination}. Check road status before travel."
    else:
        return f"It is WINTER. Suggest warm clothing. Warn about fog on highways early morning."


def get_group_tips(group_type: str, num_people: int) -> str:
    tips = {
        "family": f"FAMILY trip with {num_people} people. Add kid-friendly stops with clean restrooms every 100km. Max 4 hours driving per day.",
        "couple": "COUPLE trip. Suggest romantic viewpoints and sunset spots. Recommend boutique hotels.",
        "friends": f"FRIENDS trip with {num_people} people. Suggest adventure activities and street food spots.",
        "solo": "SOLO trip. Prioritise safety — suggest busy dhabas and well-lit stops.",
    }
    return tips.get(group_type, f"Group of {num_people} people.")


def get_budget_breakdown(budget_inr: float, num_people: int, fuel_type: str, travel_mode: str) -> str:
    per_person = budget_inr / max(num_people, 1)
    if travel_mode == "own_vehicle":
        fuel_pct = 0.30 if fuel_type != "electric" else 0.15
        return (
            f"Total budget: Rs {budget_inr:.0f} (Rs {per_person:.0f} per person). "
            f"Split: Fuel Rs {budget_inr * fuel_pct:.0f}, Tolls Rs {budget_inr * 0.10:.0f}, "
            f"Hotels Rs {budget_inr * 0.30:.0f}, Food Rs {budget_inr * 0.20:.0f}."
        )
    else:
        return (
            f"Total budget: Rs {budget_inr:.0f} (Rs {per_person:.0f} per person). "
            f"Split: Hotels Rs {budget_inr * 0.45:.0f}, Food Rs {budget_inr * 0.30:.0f}, Activities Rs {budget_inr * 0.25:.0f}."
        )


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    import math
    if not (lat1 and lon1 and lat2 and lon2):
        return 320.0
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    # Multiply by 1.3 to get realistic road distance (since roads are not straight lines)
    return round(distance * 1.3, 1)


def build_own_vehicle_prompt(trip: TripCreate, vehicle_info: dict) -> str:
    fuel_type = vehicle_info.get("fuel_type", "petrol")
    category  = vehicle_info.get("category", "car")
    mileage   = vehicle_info.get("mileage_kmpl", 15.0)
    season    = get_season(trip.start_date)
    
    lat1, lon1 = trip.origin_lat, trip.origin_lon
    lat2, lon2 = trip.destination_lat, trip.destination_lon
    dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
    
    road_trip_instructions = ""
    if dist > 400:
        road_trip_instructions = f"Since the one-way distance is {dist:.1f} km (which is > 400 km), the drive will take approximately 1.5 to 2 days to arrive safely. Therefore, structure the itinerary so that Day 1 is dedicated to highway driving (NH roads, dhabas, refuelling, and a midway night hotel stay). Day 2 morning should cover the final drive, arriving at {trip.destination} around 12:00 PM (noon) to check in and rest. Destination sightseeing and hotel stay should start on Day 2 afternoon/evening. The middle days are destination exploration, and the final day is the return journey back home."
    else:
        road_trip_instructions = f"Since the one-way distance is {dist:.1f} km (which is <= 400 km), the drive will take under 1 day. Day 1 morning/afternoon should cover the highway travel, refueling, and roadside dhaba stops, with arrival at {trip.destination} by afternoon/evening to check in. Local sightseeing should start from Day 1 evening/night."

    if trip.travel_mode == TravelMode.cab_service:
        vehicle_details = "Hired Cab Service (traveling by road in a cab with driver)."
        summary_instruction = f'7. The "ai_summary" field MUST be customized and personalized. Describe the road trip experience by Cab Service for the group size ({trip.num_people} travelers) on this specific Indian route. Do not mention "your vehicle", "mileage", or "fuel cost" as it is a hired cab.'
    else:
        vehicle_details = f"{category.upper()} running on {fuel_type.upper()} with an efficiency/mileage of {mileage} KMPL."
        summary_instruction = f'7. The "ai_summary" field MUST be customized and personalized. Mention the specific vehicle selected ({category.upper()} running on {fuel_type.upper()}) and describe the driving experience in your own vehicle for the group size ({trip.num_people} travelers) on this specific Indian route.'

    return f"""You are RoadBuddy AI, India's expert road trip planner. This entire road trip must be within INDIA only. All places, landmarks, dhabas, cities, and NH highways must be real and located in India.

Trip: {trip.origin} to {trip.destination} | {trip.start_date} to {trip.end_date}
Distance: Approximately {dist:.1f} km one-way (so total round-trip distance is {dist * 2:.1f} km).
Vehicle Selected by User: {vehicle_details}
Season: {season.upper()}
{get_budget_breakdown(trip.budget_inr, trip.num_people, fuel_type, "own_vehicle")}
Group: {get_group_tips(trip.group_type, trip.num_people)} (Total {trip.num_people} travelers)
Season tip: {get_season_tips(season, trip.destination)}

Road Trip Plan Details:
{road_trip_instructions}

Generate a complete road trip covering GOING ROUTE, DESTINATION, and RETURN ROUTE.
CRITICAL ITINERARY RULES:
1. Provide exactly 4 detailed stops for EVERY day of the trip (from Day 1 to the final day). Cover 'morning', 'afternoon', 'evening', and 'night' (such as dinners, night markets, stargazing, or rest tips) to ensure the itinerary is complete.
2. The sequence MUST represent a logical chronological progression of the day: morning (6:00 AM – 11:00 AM), afternoon (12:00 PM – 4:00 PM), evening (5:00 PM – 8:00 PM), and night (9:00 PM – 11:00 PM).
3. The "place_name" of each stop MUST start with a specific time range (e.g. "07:30 AM - HP Petrol Pump, NH-48", "01:30 PM - Midway Family Dhaba", "06:00 PM - Sunset View Point", "09:30 PM - Old Town Dinner & Nightwalk").
4. Each stop description MUST be a detailed, rich paragraph (at least 3-4 sentences, minimum 40 words) providing extensive local context, what to see, what to eat, travel advice, parking info, and specific highway safety/rest recommendations. Do not return short or generic descriptions.
5. All estimated costs ("estimated_cost_inr") for food, tickets, activities, and hotels MUST be calculated and scaled for the entire group of {trip.num_people} people (not per-person).
6. Calculate the fuel cost based on:
   - Round-trip distance of {dist * 2:.1f} km.
   - Vehicle mileage of {mileage} KMPL.
   - Average fuel prices in India: Petrol (~104 INR/L), Diesel (~94 INR/L), CNG (~85 INR/L), Electric (Rs 2.5 per km).
{summary_instruction}

Return ONLY valid JSON, no markdown:
{{
  "total_distance_km": {dist * 2},
  "fuel_cost_inr": 2400,
  "toll_cost_inr": 680,
  "return_toll_cost_inr": 680,
  "return_fuel_cost_inr": 2400,
  "hotel_cost_inr": 2500,
  "food_cost_inr": 1200,
  "total_estimated_cost_inr": 9860,
  "season": "{season}",
  "season_tip": "One key travel tip.",
  "ai_summary": "Your custom personalized summary here.",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "07:30 AM - HP Petrol Pump, NH-48, Ajmer Road, Jaipur",
      "place_type": "fuel",
      "description": "Stop at HP Petrol Pump, NH-48, Jaipur. This pump is known for high-quality fuel and fast service. Take this opportunity to fill up your tank, inspect tyre pressure, and check windshield cleanliness for safe highway driving. A small convenience store on-site allows purchasing mineral water and travel snacks before starting.",
      "estimated_cost_inr": 2400,
      "highway": "NH-48",
      "lat": null,
      "lng": null
    }}
  ]
}}
Place types: going_route, fuel, food, hotel, sightseeing, destination_food, return_route, toll"""


def build_transport_prompt(trip: TripCreate) -> str:
    season = get_season(trip.start_date)
    return f"""You are RoadBuddy AI, India's expert trip planner. This entire trip must be within INDIA only. All places, landmarks, restaurants, and cities must be real and located in India.

Destination: {trip.destination} | {trip.start_date} to {trip.end_date}
Season: {season.upper()}
{get_budget_breakdown(trip.budget_inr, trip.num_people, "na", "public")}
Group: {get_group_tips(trip.group_type, trip.num_people)} (Total {trip.num_people} travelers)

Generate a destination-only itinerary. NO highway/fuel/toll stops.
CRITICAL ITINERARY RULES:
1. Provide exactly 4 detailed stops per day covering 'morning' (activities), 'afternoon' (lunch/sightseeing), 'evening' (sunset/shopping), and 'night' (dinner/night life/rest) to ensure a complete day and night plan.
2. The sequence MUST represent a logical chronological progression of the day: morning (6:00 AM – 11:00 AM), afternoon (12:00 PM – 4:00 PM), evening (5:00 PM – 8:00 PM), and night (9:00 PM – 11:00 PM).
3. The "place_name" of each stop MUST start with a specific time range (e.g. "09:00 AM - Hadimba Devi Temple", "01:30 PM - Mall Road Cafe", "05:30 PM - Solang Valley Sunset", "08:30 PM - Johnson's Cafe Dinner").
4. Each stop description MUST be a detailed, rich paragraph (at least 3-4 sentences, minimum 40 words) providing extensive local context, what to see, what to eat, public transport guidance, and safety tips. Do not return short or generic descriptions.
5. All estimated costs ("estimated_cost_inr") for food, tickets, activities, and hotels MUST be calculated and scaled for the entire group of {trip.num_people} people (not per-person).
6. The "ai_summary" field MUST be customized and personalized. Mention the travel mode ({trip.travel_mode.value if hasattr(trip.travel_mode, 'value') else trip.travel_mode}) and describe the vacation experience for the group size ({trip.num_people} travelers) at this destination. Do not write a generic summary.

Return ONLY valid JSON, no markdown:
{{
  "total_distance_km": 0,
  "hotel_cost_inr": 3000,
  "food_cost_inr": 1500,
  "total_estimated_cost_inr": 4500,
  "season": "{season}",
  "season_tip": "One key tip.",
  "ai_summary": "Your custom personalized summary here.",
  "stops": [
    {{
      "day": 1,
      "time_slot": "morning",
      "place_name": "09:00 AM - Hadimba Devi Temple, Manali",
      "place_type": "sightseeing",
      "description": "Hadimba Devi Temple is an ancient wooden structure constructed in 1553, surrounded by a majestic cedar and deodar forest. You can view the wooden carvings on the walls and doors depicting mythological scenes, and see local artists showing rabbits and yaks. It is highly recommended to wear walking shoes as paths can be rocky and slippery, especially during monsoon season.",
      "estimated_cost_inr": 50,
      "highway": null,
      "lat": null,
      "lng": null
    }}
  ]
}}
Place types: sightseeing, hotel, destination_food"""


from app.services.groq_client import call_groq


DESTINATION_ATTRACTIONS = {
    "manali": [
        ("09:00 AM - Hadimba Devi Temple & Cedar Forest", "sightseeing", "Explore the iconic 16th-century wooden temple surrounded by giant Deodar cedar forests. Breathe fresh mountain pine air and take yak rides."),
        ("01:30 PM - Old Manali Cafe & Riverbed Lunch", "destination_food", "Enjoy wood-fired trout pizza, fresh apple cider, and mountain view coffee at a peaceful streamside cafe in Old Manali."),
        ("05:30 PM - Solang Valley Sunset & Adventure Lookout", "sightseeing", "Enjoy paragliding, ropeway rides, and breathtaking sunset views over snow-capped Himalayan peaks."),
        ("08:30 PM - Mall Road Stroll & Kullu Trout Dinner", "destination_food", "Walk down the bustling Mall Road market, shop for Himachali shawls, and savor traditional Kullu trout fish dinner.")
    ],
    "udaipur": [
        ("09:00 AM - City Palace & Maharana Museum", "sightseeing", "Explore Rajasthan's largest royal palace complex overlooking Lake Pichola. Marvel at peacock mosaics, mirror halls, and royal armory."),
        ("01:30 PM - Ambrai Ghat & Lakeview Rajasthani Lunch", "destination_food", "Dine right by the waters of Lake Pichola with magnificent views of Jagmandir and City Palace. Taste authentic Laal Maas and Gatte ki Sabzi."),
        ("05:30 PM - Lake Pichola Sunset Boat Cruise", "sightseeing", "Take a picturesque evening boat ride around Jagmandir island while watching the golden sunset paint the white marble palaces."),
        ("08:30 PM - Bagore ki Haveli Cultural Dance & Dinner", "destination_food", "Watch traditional Dharohar folk dance and puppet shows at Gangaur Ghat, followed by a romantic rooftop dinner.")
    ],
    "jaipur": [
        ("09:00 AM - Amber Fort & Sheesh Mahal", "sightseeing", "Ascend the majestic hilltop Amber Fort. Tour the mirror-adorned Sheesh Mahal, royal courtyards, and panoramic Maota Lake vistas."),
        ("01:30 PM - Laxmi Mishthan Bhandar (LMB) — Traditional Thali", "destination_food", "Feast on famous authentic Rajasthani Dal Baati Churma, Ker Sangri, and Ghewar at LMB in Johari Bazaar."),
        ("05:30 PM - Hawa Mahal & Pink City Bazaar Walk", "sightseeing", "Photograph the iconic honeycomb pink sandstone facade of Hawa Mahal, and shop for handcrafted mojris and blue pottery."),
        ("08:30 PM - Nahargarh Fort Sunset View & Dinner", "destination_food", "Drive up the winding hills to Nahargarh Fort for a breathtaking night panorama of illuminated Jaipur city while dining.")
    ],
    "goa": [
        ("09:00 AM - Fort Aguada & Sinquerim Beach Lookout", "sightseeing", "Visit the 17th-century Portuguese fortress and lighthouse standing over the Arabian Sea with panoramic coastal views."),
        ("01:30 PM - Fisherman's Wharf — Goan Seafood Lunch", "destination_food", "Savor fresh Goan fish curry rice, prawn balchão, and kokum feni at a scenic riverside shack."),
        ("05:30 PM - Baga Beach Sunset & Water Sports", "sightseeing", "Watch golden sunset waves, enjoy parasailing or jet skiing, and soak in the vibrant beach shack atmosphere."),
        ("08:30 PM - Panjim Fontainhas Latin Quarter Night Walk & Dinner", "destination_food", "Stroll through colorful Portuguese heritage streets in Panjim and dine at a boutique Goan-Mediterranean bistro.")
    ]
}


def get_destination_attractions(destination: str):
    dest = (destination or "").strip().lower()
    for key, items in DESTINATION_ATTRACTIONS.items():
        if key in dest:
            return items
    return None


def mock_own_vehicle(trip: TripCreate, vehicle_info: dict = None) -> dict:
    from datetime import datetime
    season = get_season(trip.start_date)
    
    fuel_type = vehicle_info.get("fuel_type", "petrol") if vehicle_info else "petrol"
    category = vehicle_info.get("category", "car") if vehicle_info else "car"
    mileage_kmpl = vehicle_info.get("mileage_kmpl", 15.0) if vehicle_info else 15.0
    
    # Calculate road distance
    from app.services.fuel_calculator import calculate_fuel_cost, calculate_toll_cost, estimate_distance
    
    # Try route-specific distance lookup
    dist = estimate_distance(trip.origin, trip.destination)
    if not dist or dist == 300.0:
        lat1, lon1 = trip.origin_lat, trip.origin_lon
        lat2, lon2 = trip.destination_lat, trip.destination_lon
        dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
    
    # Calculate fuel & toll using our unified calculator service
    one_way_fuel = calculate_fuel_cost(dist, mileage_kmpl, fuel_type, city=trip.origin)
    one_way_toll = calculate_toll_cost(dist, category, trip.origin, trip.destination)
    
    fuel_cost = one_way_fuel["cost_inr"]
    return_fuel_cost = fuel_cost
    
    toll_cost = one_way_toll
    return_toll_cost = toll_cost
    
    # Parse dates to calculate total trip days
    try:
        start_dt = datetime.strptime(trip.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(trip.end_date, "%Y-%m-%d")
        total_days = max((end_dt - start_dt).days + 1, 1)
    except Exception:
        total_days = 3

    # Scale hotel and food budget according to group size
    hotel_cost = round(trip.budget_inr * 0.35, 2)
    food_cost = round(trip.budget_inr * 0.20, 2)
    total_est = round(fuel_cost + return_fuel_cost + toll_cost + return_toll_cost + hotel_cost + food_cost, 2)
    
    stops = []
    is_long_dist = dist > 400
    num_p = max(trip.num_people, 1)
    
    for day in range(1, total_days + 1):
        if day == 1:
            if is_long_dist and total_days >= 3:
                # 2-day travel logic: Day 1 highway travel
                stops.extend([
                    {"day": 1, "time_slot": "morning", "place_name": f"07:30 AM - HP Petrol Pump, NH-48, {trip.origin}",
                     "place_type": "fuel", "description": f"Fill up your {fuel_type} tank at the start of your road trip. Verify tyre pressure, engine oil level, and coolant for safety. Grab refreshing beverages and light travel snacks.", "estimated_cost_inr": fuel_cost, "highway": "NH-48", "lat": None, "lng": None},
                    {"day": 1, "time_slot": "afternoon", "place_name": "01:30 PM - Midway Highway Family Dhaba",
                     "place_type": "food", "description": "Stop for a fresh highway lunch. Enjoy hot clay-oven parathas, traditional paneer curry, and sweet buttermilk while resting your legs.", "estimated_cost_inr": 250 * num_p, "highway": "NH-48", "lat": None, "lng": None},
                    {"day": 1, "time_slot": "evening", "place_name": "06:00 PM - Midway Transit Hotel & Stay",
                     "place_type": "hotel", "description": "Check in to a cozy highway motel to break the journey. Enjoy a hot shower and rest from driving.", "estimated_cost_inr": round(hotel_cost / max(total_days, 1), 2), "highway": None, "lat": None, "lng": None},
                    {"day": 1, "time_slot": "night", "place_name": "08:30 PM - Motel Restaurant & Highway Rest",
                     "place_type": "food", "description": "Relish a quiet hot dinner at the motel, inspect your vehicle, and get a restful night's sleep for tomorrow's continued journey.", "estimated_cost_inr": 200 * num_p, "highway": None, "lat": None, "lng": None}
                ])
            else:
                # Normal 1-day travel to destination
                stops.extend([
                    {"day": 1, "time_slot": "morning", "place_name": f"08:00 AM - HP Petrol Pump, NH-48, {trip.origin}",
                     "place_type": "fuel", "description": f"Fill up your {fuel_type} tank at the start of the trip. Verify tire pressure and fluid levels for safe highway travel.", "estimated_cost_inr": fuel_cost, "highway": "NH-48", "lat": None, "lng": None},
                    {"day": 1, "time_slot": "afternoon", "place_name": "01:30 PM - Apna Dhaba — Highway Lunch",
                     "place_type": "food", "description": "Stop for a fresh highway lunch. Enjoy hot parathas, paneer, and lassi while resting your legs.", "estimated_cost_inr": 250 * num_p, "highway": "NH-48", "lat": None, "lng": None},
                    {"day": 1, "time_slot": "evening", "place_name": f"05:30 PM - Hotel Shree Palace, {trip.destination}",
                     "place_type": "hotel", "description": f"Arrive at {trip.destination} and check in. Enjoy a hot shower and evening tea.", "estimated_cost_inr": round(hotel_cost / max(total_days, 1), 2), "highway": None, "lat": None, "lng": None},
                    {"day": 1, "time_slot": "night", "place_name": f"08:30 PM - Local Market & Dinner, {trip.destination}",
                     "place_type": "destination_food", "description": f"Explore the local market lanes in {trip.destination} and enjoy local specialties for dinner.", "estimated_cost_inr": 250 * num_p, "highway": None, "lat": None, "lng": None}
                ])
        elif day == 2 and is_long_dist and total_days >= 3:
            # 2-day travel logic: Day 2 arrival at noon
            stops.extend([
                {"day": 2, "time_slot": "morning", "place_name": "08:30 AM - Scenic Mountain Pass & Lookout",
                 "place_type": "going_route", "description": "Continue driving towards the destination. Pass through scenic curves or countryside roads and take short photos.", "estimated_cost_inr": 0, "highway": None, "lat": None, "lng": None},
                {"day": 2, "time_slot": "afternoon", "place_name": f"12:30 PM - Hotel Shree Palace, {trip.destination}",
                 "place_type": "hotel", "description": f"Arrive at {trip.destination} around 12:00 PM (noon). Check in, unpack, refresh and rest after the 2-day drive.", "estimated_cost_inr": round(hotel_cost / max(total_days, 1), 2), "highway": None, "lat": None, "lng": None},
                {"day": 2, "time_slot": "evening", "place_name": f"05:30 PM - Main Sightseeing Attraction, {trip.destination}",
                 "place_type": "sightseeing", "description": f"Start exploring the top spots in {trip.destination}. Hire a local guide and enjoy the architecture.", "estimated_cost_inr": 100 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": 2, "time_slot": "night", "place_name": f"08:30 PM - Traditional Restaurant & Dinner, {trip.destination}",
                 "place_type": "destination_food", "description": "Enjoy a delicious dinner in the old town, sampling local curries and traditional desserts.", "estimated_cost_inr": 300 * num_p, "highway": None, "lat": None, "lng": None}
            ])
        elif day == total_days and total_days > 1:
            # Last Day: Return home
            stops.extend([
                {"day": day, "time_slot": "morning", "place_name": f"08:30 AM - Indian Oil Pump, {trip.destination}",
                 "place_type": "fuel", "description": f"Refuel your {fuel_type} tank for the return journey. Clean windshield and verify tire pressure.", "estimated_cost_inr": return_fuel_cost, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "afternoon", "place_name": "01:30 PM - Midway Highway Food Court",
                 "place_type": "food", "description": "Stop at a modern food court for lunch, offering North and South Indian dining options.", "estimated_cost_inr": 250 * num_p, "highway": "NH-48", "lat": None, "lng": None},
                {"day": day, "time_slot": "evening", "place_name": f"06:00 PM - Home — {trip.origin}",
                 "place_type": "return_route", "description": f"Complete the journey and arrive back in {trip.origin}. Unload bags and relax after an amazing road trip.", "estimated_cost_inr": 0, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "night", "place_name": f"09:00 PM - Home Sweet Home, {trip.origin}",
                 "place_type": "return_route", "description": "Rest at home. Share your favorite road trip moments and mileage stats with friends on RoadBuddy.", "estimated_cost_inr": 0, "highway": None, "lat": None, "lng": None}
            ])
        else:
            # Middle Exploration Days
            custom_attr = get_destination_attractions(trip.destination)
            if custom_attr:
                stops.extend([
                    {"day": day, "time_slot": "morning", "place_name": custom_attr[0][0], "place_type": custom_attr[0][1], "description": custom_attr[0][2], "estimated_cost_inr": 150 * num_p, "highway": None, "lat": None, "lng": None},
                    {"day": day, "time_slot": "afternoon", "place_name": custom_attr[1][0], "place_type": custom_attr[1][1], "description": custom_attr[1][2], "estimated_cost_inr": 250 * num_p, "highway": None, "lat": None, "lng": None},
                    {"day": day, "time_slot": "evening", "place_name": custom_attr[2][0], "place_type": custom_attr[2][1], "description": custom_attr[2][2], "estimated_cost_inr": 150 * num_p, "highway": None, "lat": None, "lng": None},
                    {"day": day, "time_slot": "night", "place_name": custom_attr[3][0], "place_type": custom_attr[3][1], "description": custom_attr[3][2], "estimated_cost_inr": 350 * num_p, "highway": None, "lat": None, "lng": None}
                ])
            else:
                stops.extend([
                    {"day": day, "time_slot": "morning", "place_name": f"09:00 AM - Top Sightseeing Spot, {trip.destination}",
                     "place_type": "sightseeing", "description": f"Visit iconic landmarks and scenic viewpoints in {trip.destination}. Take pictures, breathe fresh air, and enjoy local nature hikes.", "estimated_cost_inr": 100 * num_p, "highway": None, "lat": None, "lng": None},
                    {"day": day, "time_slot": "afternoon", "place_name": f"01:30 PM - Famous Local Cafe & Lunch, {trip.destination}",
                     "place_type": "destination_food", "description": f"Savor authentic regional cuisine and wood-fired specialties at a highly recommended eatery in {trip.destination}.", "estimated_cost_inr": 250 * num_p, "highway": None, "lat": None, "lng": None},
                    {"day": day, "time_slot": "evening", "place_name": f"05:30 PM - Heritage Walk & Sunset Point, {trip.destination}",
                     "place_type": "sightseeing", "description": f"Explore local heritage streets, handicrafts showrooms, and buy traditional artwork in {trip.destination}.", "estimated_cost_inr": 100 * num_p, "highway": None, "lat": None, "lng": None},
                    {"day": day, "time_slot": "night", "place_name": f"08:30 PM - Traditional Dinner & Nightwalk, {trip.destination}",
                     "place_type": "destination_food", "description": f"Enjoy dinner at a courtyard restaurant and stroll through illuminated night market lanes in {trip.destination}.", "estimated_cost_inr": 350 * num_p, "highway": None, "lat": None, "lng": None}
                ])
            
    return {
        "total_distance_km": dist * 2,
        "fuel_cost_inr": fuel_cost,
        "toll_cost_inr": toll_cost,
        "return_fuel_cost_inr": return_fuel_cost,
        "return_toll_cost_inr": return_toll_cost,
        "hotel_cost_inr": hotel_cost,
        "food_cost_inr": food_cost,
        "total_estimated_cost_inr": total_est,
        "season": season,
        "season_tip": "Check road conditions and tyre pressure before leaving.",
        "ai_summary": (
            f"A personalized road trip from {trip.origin} to {trip.destination} for a group of {num_p} ({trip.group_type}) by Cab Service."
            if trip.travel_mode == TravelMode.cab_service else
            f"A personalized road trip from {trip.origin} to {trip.destination} for a group of {num_p} ({trip.group_type}) in your {fuel_type.upper()} {category.upper()} (Mileage: {mileage_kmpl} KMPL)."
        ),
        "stops": stops
    }


def mock_transport_itinerary(trip: TripCreate) -> dict:
    from datetime import datetime
    season = get_season(trip.start_date)
    
    try:
        start_dt = datetime.strptime(trip.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(trip.end_date, "%Y-%m-%d")
        total_days = max((end_dt - start_dt).days + 1, 1)
    except Exception:
        total_days = 3

    num_p = max(trip.num_people, 1)
    hotel_cost = round(trip.budget_inr * 0.45, 2)
    food_cost = round(trip.budget_inr * 0.30, 2)
    total_est = round(hotel_cost + food_cost, 2)

    stops = []
    for day in range(1, total_days + 1):
        if day == 1:
            stops.extend([
                {"day": 1, "time_slot": "morning", "place_name": f"09:00 AM - Arrival & Top Attraction, {trip.destination}",
                 "place_type": "sightseeing", "description": "Arrive at your destination and check out the top local attraction. Marvel at the stunning architecture, take pictures, and explore the museum or courtyards with local guide explanations.", "estimated_cost_inr": 150 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": 1, "time_slot": "afternoon", "place_name": "01:30 PM - Local Food Street",
                 "place_type": "destination_food", "description": "Indulge in delicious local street food for lunch. Discover regional flavors, sample traditional street desserts, and talk to local stall vendors about popular cultural eats.", "estimated_cost_inr": 250 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": 1, "time_slot": "evening", "place_name": "05:30 PM - Hotel Grand Inn",
                 "place_type": "hotel", "description": "Check in at Hotel Grand Inn, unpack your luggage, and refresh after your journey. The hotel offers clean rooms, modern amenities, and cozy bedding for a relaxing evening rest.", "estimated_cost_inr": round(hotel_cost / max(total_days, 1), 2), "highway": None, "lat": None, "lng": None},
                {"day": 1, "time_slot": "night", "place_name": "08:30 PM - Main Street Bazar & Dinner",
                 "place_type": "destination_food", "description": "Walk around the lively main street bazar illuminated by colorful lights. Pick up souvenirs and local products, and settle down at a recommended local restaurant for an authentic traditional dinner.", "estimated_cost_inr": 250 * num_p, "highway": None, "lat": None, "lng": None},
            ])
        elif day == total_days and total_days > 1:
            stops.extend([
                {"day": day, "time_slot": "morning", "place_name": f"09:00 AM - Souvenir Shopping, {trip.destination}",
                 "place_type": "sightseeing", "description": "Spend your final morning buying souvenirs, local handicrafts, and specialty sweets to take back home.", "estimated_cost_inr": 100 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "afternoon", "place_name": "01:30 PM - Farewell Lunch",
                 "place_type": "destination_food", "description": "Enjoy a final lunch at a popular cafe, reminiscing about the highlights of your trip.", "estimated_cost_inr": 250 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "evening", "place_name": "05:30 PM - Departure Terminal / Station",
                 "place_type": "sightseeing", "description": "Head to the departure terminal or train station to begin your travel back.", "estimated_cost_inr": 0, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "night", "place_name": "09:00 PM - Arrive Back Home",
                 "place_type": "sightseeing", "description": "Arrive safely back home, unpack your bags, and get a peaceful night's rest.", "estimated_cost_inr": 0, "highway": None, "lat": None, "lng": None},
            ])
        else:
            stops.extend([
                {"day": day, "time_slot": "morning", "place_name": f"09:00 AM - Sightseeing Exploration, {trip.destination}",
                 "place_type": "sightseeing", "description": "Explore the famous spots, temples, scenic parks, or valley viewpoints in the region.", "estimated_cost_inr": 100 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "afternoon", "place_name": "01:30 PM - Traditional Cuisine Lunch",
                 "place_type": "destination_food", "description": "Have an authentic lunch at a heritage restaurant specializing in regional cuisine.", "estimated_cost_inr": 200 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "evening", "place_name": "05:30 PM - Lakeside / Mountain Sunset Walk",
                 "place_type": "sightseeing", "description": "Stroll around scenic waterfronts or sunset points to enjoy the peaceful evening atmosphere.", "estimated_cost_inr": 50 * num_p, "highway": None, "lat": None, "lng": None},
                {"day": day, "time_slot": "night", "place_name": "08:30 PM - Local Dinner & Nightwalk",
                 "place_type": "destination_food", "description": "Have dinner at a cozy eatery and walk around the quiet lanes before heading back to the hotel.", "estimated_cost_inr": 250 * num_p, "highway": None, "lat": None, "lng": None},
            ])
            
    return {
        "total_distance_km": 0,
        "hotel_cost_inr": hotel_cost,
        "food_cost_inr": food_cost,
        "total_estimated_cost_inr": total_est,
        "season": season,
        "season_tip": "Carry appropriate clothing and check transit schedules.",
        "ai_summary": f"A personalized vacation in {trip.destination} for {num_p} travelers ({trip.group_type}) traveling by {trip.travel_mode.value if hasattr(trip.travel_mode, 'value') else trip.travel_mode}.",
        "stops": stops
    }


async def generate_itinerary(trip: TripCreate, vehicle_info: dict) -> TripOut:
    try:
        is_road_trip = (trip.travel_mode == TravelMode.own_vehicle or trip.travel_mode == TravelMode.cab_service)
        
        if is_road_trip:
            if not vehicle_info:
                vehicle_info = {
                    "fuel_type": "petrol",
                    "category": "car",
                    "mileage_kmpl": 15.0
                }
            if settings.gemini_api_key:
                try:
                    data = await call_groq(build_own_vehicle_prompt(trip, vehicle_info))
                except Exception as e:
                    print(f"Gemini itinerary failed: {e}. Falling back to mock.")
                    data = mock_own_vehicle(trip, vehicle_info)
            else:
                data = mock_own_vehicle(trip, vehicle_info)
        else:
            if settings.gemini_api_key:
                try:
                    data = await call_groq(build_transport_prompt(trip))
                except Exception as e:
                    print(f"Gemini itinerary failed: {e}. Falling back to mock.")
                    data = mock_transport_itinerary(trip)
            else:
                data = mock_transport_itinerary(trip)

        stops = [ItineraryStop(**s) for s in data["stops"]]
        import uuid
        trip_uuid = uuid.uuid4().hex[:6]
        trip_id = f"trip_{trip.origin[:3].lower()}{trip.destination[:3].lower()}_{trip_uuid}"
        
        if trip.travel_mode == TravelMode.own_vehicle:
            # Recalculate using our updated fuel_calculator logic to ensure 100% real values
            from app.services.fuel_calculator import calculate_fuel_cost, calculate_toll_cost, estimate_distance
            
            route_dist = estimate_distance(trip.origin, trip.destination)
            if not route_dist or route_dist == 300.0:
                lat1, lon1 = trip.origin_lat, trip.origin_lon
                lat2, lon2 = trip.destination_lat, trip.destination_lon
                route_dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
            
            v_info = vehicle_info or {"fuel_type": "petrol", "category": "car", "mileage_kmpl": 15.0}
            fuel_type = v_info.get("fuel_type", "petrol")
            mileage = v_info.get("mileage_kmpl", 15.0)
            category = v_info.get("category", "car")
            
            one_way_fuel = calculate_fuel_cost(route_dist, mileage, fuel_type, city=trip.origin)
            one_way_toll = calculate_toll_cost(route_dist, category, trip.origin, trip.destination)
            
            fuel_cost = round(one_way_fuel["cost_inr"] * 2, 2)
            toll_cost = round(one_way_toll * 2, 2)
            total_distance = round(route_dist * 2, 2)
            
            hotel_cost = data.get("hotel_cost_inr", 0)
            food_cost = data.get("food_cost_inr", 0)
            total_estimated_cost = round(fuel_cost + toll_cost + hotel_cost + food_cost, 2)
        else:
            fuel_cost = data.get("fuel_cost_inr", 0) + data.get("return_fuel_cost_inr", 0)
            toll_cost = data.get("toll_cost_inr", 0) + data.get("return_toll_cost_inr", 0)
            total_distance = data.get("total_distance_km", 0)
            total_estimated_cost = data.get("total_estimated_cost_inr", 0)
        
        return TripOut(
            id=trip_id,
            origin=trip.origin, destination=trip.destination, travel_mode=trip.travel_mode,
            total_distance_km=total_distance, stops=stops,
            fuel_cost_inr=fuel_cost,
            toll_cost_inr=toll_cost,
            transport_fare_inr=0, return_fare_inr=0,
            hotel_cost_inr=data.get("hotel_cost_inr", 0),
            food_cost_inr=data.get("food_cost_inr", 0),
            total_estimated_cost_inr=total_estimated_cost,
            ai_summary=data.get("ai_summary", ""),
        )
    except Exception as e:
        raise RuntimeError(f"Itinerary generation failed: {e}") from e