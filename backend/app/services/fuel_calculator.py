"""
Fuel & Toll Calculator Service
-------------------------------
In production:
  - Fetch real fuel prices from the Indian Oil / Petrol Price API
  - Fetch NHAI toll data from the FASTag API
  - Get route distance from Google Maps Distance Matrix API

For now we use realistic mock data so you can build and test
the full API without needing any API keys.
"""

# Approximate fuel prices (₹ per litre/unit) by fuel type
FUEL_PRICES = {
    "petrol":   104.0,
    "diesel":    90.0,
    "cng":       85.0,   # per kg
    "electric":   8.5,   # per kWh
}

# Approximate toll rates (₹ per km on NH) by vehicle category
TOLL_RATE_PER_KM = {
    "two_wheeler":  0.35,
    "car":          0.65,
    "suv":          0.80,
    "van":          1.10,
}


def calculate_fuel_cost(
    distance_km: float,
    mileage_kmpl: float,
    fuel_type: str,
    city: str = "Jaipur",
) -> dict:
    price = FUEL_PRICES.get(fuel_type, 104.0)
    units_required = distance_km / mileage_kmpl
    cost = units_required * price
    return {
        "units_required": round(units_required, 2),
        "cost_inr": round(cost, 2),
        "price_per_unit": price,
        "fuel_type": fuel_type,
        "city": city,
    }


def calculate_toll_cost(distance_km: float, vehicle_category: str) -> float:
    rate = TOLL_RATE_PER_KM.get(vehicle_category, 0.65)
    return round(distance_km * rate, 2)


def estimate_distance(origin: str, destination: str) -> float:
    """
    Mock distance estimation.
    Replace with Google Maps Distance Matrix API call in production:
      GET https://maps.googleapis.com/maps/api/distancematrix/json
          ?origins={origin}&destinations={destination}&key={API_KEY}
    """
    # Very rough estimate — 2 km per character difference as a placeholder
    mock_distances = {
        ("jaipur", "udaipur"):   400,
        ("jaipur", "delhi"):     280,
        ("mumbai", "pune"):      150,
        ("delhi", "agra"):       230,
        ("bengaluru", "mysuru"): 145,
        ("chennai", "pondicherry"): 160,
    }
    key = (origin.lower().strip(), destination.lower().strip())
    reverse_key = (destination.lower().strip(), origin.lower().strip())
    return mock_distances.get(key) or mock_distances.get(reverse_key) or 300.0


def build_fuel_calc_response(
    origin: str,
    destination: str,
    vehicle: dict,   # {fuel_type, mileage_kmpl, category}
    include_return: bool = False,
) -> dict:
    distance = estimate_distance(origin, destination)
    fuel = calculate_fuel_cost(
        distance,
        vehicle["mileage_kmpl"],
        vehicle["fuel_type"],
    )
    toll = calculate_toll_cost(distance, vehicle["category"])

    total_one_way = round(fuel["cost_inr"] + toll, 2)
    total_return  = round(total_one_way * 2, 2) if include_return else None

    return {
        "distance_km": distance,
        "fuel_litres_required": fuel["units_required"],
        "fuel_cost_inr": fuel["cost_inr"],
        "toll_cost_inr": toll,
        "total_one_way_inr": total_one_way,
        "total_with_return_inr": total_return,
        "fuel_price_per_litre": fuel["price_per_unit"],
        "city": origin,
    }
