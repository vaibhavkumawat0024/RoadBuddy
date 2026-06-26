"""
Transport Service — RoadBuddy
-------------------------------------
Queries buses, trains, and flights from the local database.
"""

from sqlalchemy.orm import Session
from app.schemas.schemas import TransportOption, TransportMode


def _extract_numeric_id(option_id: str) -> int | None:
    """Extract the numeric DB id from an option_id like 'bus_3' -> 3."""
    if not option_id:
        return None
    try:
        return int(option_id.rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return None


def get_transit_stops_and_amenities(origin: str, destination: str, mode: str, operator: str = "", option_id: str = "") -> tuple[list[dict], list[str]]:
    orig = origin.strip().lower()
    dest = destination.strip().lower()
    m_val = mode.strip().lower()
    op_lower = operator.lower()
    numeric_id = _extract_numeric_id(option_id)
    is_odd = numeric_id is not None and numeric_id % 2 == 1
    is_even = numeric_id is not None and numeric_id % 2 == 0

    stops = []
    complimentary = []

    # 1. Determine Complimentary Items
    if m_val == "bus":
        complimentary = ["Water Bottle", "USB Charging Port"]
        if "volvo" in op_lower or "ac" in op_lower or "smartbus" in op_lower or "zingbus" in op_lower:
            complimentary.extend(["Blanket", "Complimentary Snacks"])
    elif m_val == "train":
        complimentary = ["Charging Socket", "Bedroll & Pillow"]
        if any(x in op_lower for x in ["rajdhani", "shatabdi", "vande bharat", "duronto"]):
            complimentary.extend(["Meals Included (Breakfast/Dinner)", "Complimentary Tea & Coffee"])
    elif m_val == "flight":
        complimentary = ["In-flight Entertainment", "15kg Checked Baggage", "7kg Cabin Baggage"]
        if any(x in op_lower for x in ["vistara", "air india"]):
            complimentary.append("Free Hot Meals & Beverages")
        else:
            complimentary.append("Complimentary Water & Snack")
    elif m_val == "cab":
        complimentary = ["Water Bottle", "Air Conditioning", "Mobile Charger"]
    else:
        complimentary = ["Complimentary Water"]

    # 2. Determine Stops (operator-aware)
    # Case A: Jaipur <-> Udaipur
    if ("jaipur" in orig and "udaipur" in dest) or ("udaipur" in orig and "jaipur" in dest):
        if m_val in ("bus", "cab"):
            if "zingbus" in op_lower or is_odd:
                stops = [
                    {"name": "Kishangarh", "duration_mins": 10, "lat": 26.5885, "lon": 74.8574},
                    {"name": "Beawar", "duration_mins": 15, "lat": 26.1011, "lon": 74.3189},
                    {"name": "Bhilwara", "duration_mins": 20, "lat": 25.3475, "lon": 74.6405},
                ]
            elif "intrcity" in op_lower or is_even:
                stops = [
                    {"name": "Ajmer Bypass", "duration_mins": 20, "lat": 26.4498, "lon": 74.6399},
                    {"name": "Chittorgarh", "duration_mins": 15, "lat": 24.8887, "lon": 74.6269},
                    {"name": "Nathdwara", "duration_mins": 10, "lat": 24.9384, "lon": 73.8230},
                ]
            else:
                stops = [
                    {"name": "Pushkar Turn", "duration_mins": 15, "lat": 26.4851, "lon": 74.5532},
                    {"name": "Devgarh", "duration_mins": 10, "lat": 25.5329, "lon": 73.8935},
                ]
        elif m_val == "train":
            if "chetak" in op_lower or "mewar" in op_lower:
                stops = [
                    {"name": "Ajmer Jn", "duration_mins": 10, "lat": 26.4560, "lon": 74.6444},
                    {"name": "Bhilwara", "duration_mins": 5, "lat": 25.3475, "lon": 74.6405},
                    {"name": "Mavli Jn", "duration_mins": 3, "lat": 24.9038, "lon": 73.8787},
                    {"name": "Chanderiya", "duration_mins": 2, "lat": 24.9317, "lon": 74.6200},
                ]
            elif "shatabdi" in op_lower or "vande" in op_lower:
                stops = [
                    {"name": "Phulera Jn", "duration_mins": 2, "lat": 26.8731, "lon": 75.2372},
                    {"name": "Ajmer Jn", "duration_mins": 5, "lat": 26.4560, "lon": 74.6444},
                    {"name": "Chittorgarh Jn", "duration_mins": 8, "lat": 24.8887, "lon": 74.6269},
                ]
            else:
                stops = [
                    {"name": "Ajmer Jn", "duration_mins": 8, "lat": 26.4560, "lon": 74.6444},
                    {"name": "Bhilwara", "duration_mins": 3, "lat": 25.3475, "lon": 74.6405},
                    {"name": "Chanderiya", "duration_mins": 2, "lat": 24.9317, "lon": 74.6200},
                ]

    # Case B: Jaipur <-> Delhi
    elif ("jaipur" in orig and "delhi" in dest) or ("delhi" in orig and "jaipur" in dest):
        if m_val in ("bus", "cab"):
            if "zingbus" in op_lower or is_odd:
                stops = [
                    {"name": "Shahpura", "duration_mins": 10, "lat": 27.3865, "lon": 75.9590},
                    {"name": "Kotputli", "duration_mins": 20, "lat": 27.7022, "lon": 76.1983},
                    {"name": "Manesar", "duration_mins": 15, "lat": 28.3597, "lon": 76.9354},
                ]
            else:
                stops = [
                    {"name": "Behror", "duration_mins": 25, "lat": 27.8875, "lon": 76.2974},
                    {"name": "Dharuhera", "duration_mins": 15, "lat": 28.2054, "lon": 76.7964},
                ]
        elif m_val == "train":
            if "shatabdi" in op_lower or "rajdhani" in op_lower:
                stops = [
                    {"name": "Bandikui Jn", "duration_mins": 2, "lat": 27.0481, "lon": 76.5704},
                    {"name": "Alwar Jn", "duration_mins": 3, "lat": 27.5684, "lon": 76.6234},
                    {"name": "Rewari Jn", "duration_mins": 5, "lat": 28.1970, "lon": 76.6153},
                    {"name": "Gurgaon", "duration_mins": 2, "lat": 28.4595, "lon": 77.0266},
                ]
            else:
                stops = [
                    {"name": "Alwar Jn", "duration_mins": 5, "lat": 27.5684, "lon": 76.6234},
                    {"name": "Gurgaon", "duration_mins": 2, "lat": 28.4595, "lon": 77.0266},
                ]

    # Case C: Delhi <-> Manali
    elif ("delhi" in orig and "manali" in dest) or ("manali" in orig and "delhi" in dest):
        if m_val in ("bus", "cab"):
            if "volvo" in op_lower or is_odd:
                stops = [
                    {"name": "Karnal", "duration_mins": 15, "lat": 29.6857, "lon": 76.9905},
                    {"name": "Chandigarh", "duration_mins": 30, "lat": 30.7333, "lon": 76.7794},
                    {"name": "Bilaspur", "duration_mins": 10, "lat": 31.3404, "lon": 76.7612},
                    {"name": "Mandi", "duration_mins": 20, "lat": 31.7087, "lon": 76.9320},
                ]
            else:
                stops = [
                    {"name": "Ambala", "duration_mins": 20, "lat": 30.3782, "lon": 76.7767},
                    {"name": "Sundernagar", "duration_mins": 15, "lat": 31.5338, "lon": 76.9048},
                    {"name": "Mandi", "duration_mins": 15, "lat": 31.7087, "lon": 76.9320},
                ]
        elif m_val == "train":
            if "shatabdi" in op_lower:
                stops = [
                    {"name": "Karnal", "duration_mins": 2, "lat": 29.6857, "lon": 76.9905},
                    {"name": "Ambala Cantt", "duration_mins": 5, "lat": 30.3610, "lon": 76.8241},
                    {"name": "Chandigarh Jn", "duration_mins": 10, "lat": 30.7061, "lon": 76.8013},
                ]
            else:
                stops = [
                    {"name": "Ambala Cantt", "duration_mins": 10, "lat": 30.3610, "lon": 76.8241},
                    {"name": "Chandigarh Jn", "duration_mins": 15, "lat": 30.7061, "lon": 76.8013},
                ]

    # Case D: Mumbai <-> Goa
    elif ("mumbai" in orig and "goa" in dest) or ("goa" in orig and "mumbai" in dest):
        if m_val in ("bus", "cab"):
            if "neeta" in op_lower or is_odd:
                stops = [
                    {"name": "Panvel", "duration_mins": 15, "lat": 18.9894, "lon": 73.1175},
                    {"name": "Pune Bypass", "duration_mins": 20, "lat": 18.5204, "lon": 73.8567},
                    {"name": "Kolhapur", "duration_mins": 25, "lat": 16.7050, "lon": 74.2433},
                    {"name": "Sawantwadi", "duration_mins": 10, "lat": 15.9023, "lon": 73.8195},
                ]
            else:
                stops = [
                    {"name": "Pune Expressway Stop", "duration_mins": 25, "lat": 18.5204, "lon": 73.8567},
                    {"name": "Ratnagiri", "duration_mins": 20, "lat": 16.9944, "lon": 73.3000},
                ]
        elif m_val == "train":
            if "rajdhani" in op_lower or "konkan" in op_lower:
                stops = [
                    {"name": "Panvel Jn", "duration_mins": 5, "lat": 18.9894, "lon": 73.1175},
                    {"name": "Ratnagiri", "duration_mins": 5, "lat": 16.9944, "lon": 73.3000},
                    {"name": "Kudal", "duration_mins": 3, "lat": 16.0106, "lon": 73.6857},
                    {"name": "Madgaon Jn", "duration_mins": 10, "lat": 15.2755, "lon": 73.9582},
                ]
            else:
                stops = [
                    {"name": "Ratnagiri", "duration_mins": 5, "lat": 16.9944, "lon": 73.3000},
                    {"name": "Madgaon Jn", "duration_mins": 10, "lat": 15.2755, "lon": 73.9582},
                ]

    # General Fallback for arbitrary routes
    if not stops and m_val != "flight":
        coords = {
            "delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "jaipur": (26.9124, 75.7873),
            "udaipur": (24.5854, 73.7125), "goa": (15.2993, 74.1240), "manali": (32.2396, 77.1887),
            "jodhpur": (26.2389, 73.0243), "agra": (27.1767, 78.0081), "shimla": (31.1048, 77.1734),
            "bangalore": (12.9716, 77.5946), "kolkata": (22.5726, 88.3639), "pune": (18.5204, 73.8567),
            "chennai": (13.0827, 80.2707), "hyderabad": (17.3850, 78.4867)
        }

        c1, c2 = None, None
        for k, v in coords.items():
            if k in orig:
                c1 = v
            if k in dest:
                c2 = v

        if c1 and c2:
            mid_lat = (c1[0] + c2[0]) / 2
            mid_lon = (c1[1] + c2[1]) / 2
            stops = [
                {"name": "Midway Highway Stop", "duration_mins": 20, "lat": mid_lat, "lon": mid_lon}
            ]
        else:
            stops = [
                {"name": "Midway Transit Stop", "duration_mins": 20, "lat": 26.0, "lon": 76.0}
            ]

    return stops, complimentary


def get_transit_stations(origin: str, destination: str, mode: str) -> tuple[tuple[str, float, float], tuple[str, float, float]]:
    orig = origin.strip().lower()
    dest = destination.strip().lower()
    m_val = mode.strip().lower()

    if m_val not in ("bus", "train", "flight"):
        sfx = "Station"
        if m_val == "cab":
            sfx = "Pickup Point"
        o_name = f"{origin} {sfx}"
        d_name = f"{destination} {sfx}"
        o_lat, o_lon = 26.0, 76.0
        d_lat, d_lon = 26.0, 76.0
        coords = {
            "delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "jaipur": (26.9124, 75.7873),
            "udaipur": (24.5854, 73.7125), "goa": (15.2993, 74.1240), "manali": (32.2396, 77.1887),
            "jodhpur": (26.2389, 73.0243), "agra": (27.1767, 78.0081), "shimla": (31.1048, 77.1734),
            "bangalore": (12.9716, 77.5946), "kolkata": (22.5726, 88.3639), "pune": (18.5204, 73.8567),
            "chennai": (13.0827, 80.2707), "hyderabad": (17.3850, 78.4867)
        }
        for city, v in coords.items():
            if city in orig:
                o_lat, o_lon = v
            if city in dest:
                d_lat, d_lon = v
        return (o_name, o_lat, o_lon), (d_name, d_lat, d_lon)

    stations_data = {
        "jaipur": {
            "bus": ("Jaipur Sindhi Camp Bus Stand", 26.9248, 75.7985),
            "train": ("Jaipur Jn Railway Station", 26.9197, 75.7878),
            "flight": ("Jaipur International Airport (JAI)", 26.8289, 75.8122),
        },
        "udaipur": {
            "bus": ("Udaipur Central Bus Stand", 24.5801, 73.7027),
            "train": ("Udaipur City Railway Station", 24.5714, 73.6967),
            "flight": ("Maharana Pratap Airport Udaipur (UDR)", 24.6125, 73.8961),
        },
        "delhi": {
            "bus": ("ISBT Kashmiri Gate Bus Stand", 28.6675, 77.2282),
            "train": ("New Delhi Railway Station (NDLS)", 28.6430, 77.2223),
            "flight": ("Indira Gandhi International Airport (DEL)", 28.5562, 77.1000),
        },
        "manali": {
            "bus": ("Manali Private Volvo Bus Stand", 32.2396, 77.1887),
            "train": ("Chandigarh Junction Station", 30.7061, 76.8013),
            "flight": ("Kullu-Manali Bhuntar Airport (KUU)", 31.8767, 77.1541),
        },
        "mumbai": {
            "bus": ("Mumbai Central Bus Depot", 18.9723, 72.8188),
            "train": ("CSMT Railway Station Mumbai", 18.9400, 72.8354),
            "flight": ("CSM International Airport (BOM)", 19.0896, 72.8656),
        },
        "goa": {
            "bus": ("Panaji Kadam Bus Stand", 15.4950, 73.8340),
            "train": ("Madgaon Junction Railway Station", 15.2755, 73.9582),
            "flight": ("Manohar International Airport Goa (GOX)", 15.7291, 73.8728),
        },
        "jodhpur": {
            "bus": ("Jodhpur Central Bus Stand", 26.2694, 73.0309),
            "train": ("Jodhpur Junction Railway Station", 26.2863, 73.0163),
            "flight": ("Jodhpur Airport (JDH)", 26.2514, 73.0486),
        },
        "agra": {
            "bus": ("ISBT Agra Bus Stand", 27.2155, 77.9622),
            "train": ("Agra Cantt Railway Station", 27.1587, 78.0068),
            "flight": ("Agra Airport (AGR)", 27.1558, 77.9611),
        },
        "shimla": {
            "bus": ("Shimla ISBT Tutikandi", 31.0967, 77.1420),
            "train": ("Shimla Railway Station", 31.1030, 77.1610),
            "flight": ("Shimla Airport (SLV)", 31.0818, 77.0683),
        },
        "bangalore": {
            "bus": ("Kempegowda Bus Station (Majestic)", 12.9779, 77.5729),
            "train": ("KSR Bengaluru City Railway Station", 12.9781, 77.5697),
            "flight": ("Kempegowda International Airport (BLR)", 13.1986, 77.7066),
        },
        "kolkata": {
            "bus": ("Esplanade Bus Terminus", 22.5647, 88.3517),
            "train": ("Howrah Junction Railway Station", 22.5836, 88.3414),
            "flight": ("Netaji Subhash Chandra Bose International Airport (CCU)", 22.6547, 88.4467),
        },
        "pune": {
            "bus": ("Swargate Bus Station", 18.5018, 73.8587),
            "train": ("Pune Junction Railway Station", 18.5289, 73.8744),
            "flight": ("Pune International Airport (PNQ)", 18.5822, 73.9197),
        },
        "chennai": {
            "bus": ("Koyambedu CMBT", 13.0678, 80.2056),
            "train": ("Chennai Central Railway Station", 13.0827, 80.2754),
            "flight": ("Chennai International Airport (MAA)", 12.9941, 80.1709),
        },
        "hyderabad": {
            "bus": ("Mahatma Gandhi Bus Station (MGBS)", 17.3776, 78.4839),
            "train": ("Secunderabad Junction Railway Station", 17.4344, 78.5017),
            "flight": ("Rajiv Gandhi International Airport (HYD)", 17.2403, 78.4294),
        }
    }

    o_res = None
    d_res = None

    for city, modes in stations_data.items():
        if city in orig:
            o_res = modes.get(m_val)
        if city in dest:
            d_res = modes.get(m_val)

    if o_res is None:
        suffix = {
            "bus": "Central Bus Station",
            "train": "Junction Railway Station",
            "flight": "Airport"
        }
        sfx = suffix.get(m_val, "Station")
        o_name = f"{origin} {sfx}"
        o_lat, o_lon = 26.0, 76.0
        coords = {
            "delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "jaipur": (26.9124, 75.7873),
            "udaipur": (24.5854, 73.7125), "goa": (15.2993, 74.1240), "manali": (32.2396, 77.1887),
            "jodhpur": (26.2389, 73.0243), "agra": (27.1767, 78.0081), "shimla": (31.1048, 77.1734),
            "bangalore": (12.9716, 77.5946), "kolkata": (22.5726, 88.3639), "pune": (18.5204, 73.8567),
            "chennai": (13.0827, 80.2707), "hyderabad": (17.3850, 78.4867)
        }
        for city in coords:
            if city in orig:
                o_lat, o_lon = coords[city]
                break
        o_res = (o_name, o_lat, o_lon)

    if d_res is None:
        suffix = {
            "bus": "Central Bus Station",
            "train": "Junction Railway Station",
            "flight": "Airport"
        }
        sfx = suffix.get(m_val, "Station")
        d_name = f"{destination} {sfx}"
        d_lat, d_lon = 26.0, 76.0
        coords = {
            "delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "jaipur": (26.9124, 75.7873),
            "udaipur": (24.5854, 73.7125), "goa": (15.2993, 74.1240), "manali": (32.2396, 77.1887),
            "jodhpur": (26.2389, 73.0243), "agra": (27.1767, 78.0081), "shimla": (31.1048, 77.1734),
            "bangalore": (12.9716, 77.5946), "kolkata": (22.5726, 88.3639), "pune": (18.5204, 73.8567),
            "chennai": (13.0827, 80.2707), "hyderabad": (17.3850, 78.4867)
        }
        for city in coords:
            if city in dest:
                d_lat, d_lon = coords[city]
                break
        d_res = (d_name, d_lat, d_lon)

    return o_res, d_res


def search_transport(origin: str, destination: str, mode: str, db: Session) -> list:
    """
    Search available buses, trains, or flights in the database.
    """
    origin_clean = origin.strip().lower()
    dest_clean = destination.strip().lower()
    
    results = []
    
    if mode == TransportMode.bus:
        from app.models.models import Bus
        buses = db.query(Bus).filter(
            Bus.origin.ilike(f"%{origin_clean}%"),
            Bus.destination.ilike(f"%{dest_clean}%")
        ).all()
        for b in buses:
            stops, items = get_transit_stops_and_amenities(b.origin, b.destination, "bus", b.operator_name, f"bus_{b.id}")
            (o_st_name, o_st_lat, o_st_lon), (d_st_name, d_st_lat, d_st_lon) = get_transit_stations(b.origin, b.destination, "bus")
            results.append(TransportOption(
                id=f"bus_{b.id}",
                origin=b.origin,
                destination=b.destination,
                mode=TransportMode.bus,
                operator=b.operator_name,
                departure_time=b.departure_time,
                arrival_time=b.arrival_time,
                duration_hrs=b.duration_hrs,
                fare_inr=b.fare_inr,
                seats_available=b.seats_available,
                intermediate_stops=stops,
                complimentary_items=items,
                origin_station_name=o_st_name,
                origin_lat=o_st_lat,
                origin_lon=o_st_lon,
                destination_station_name=d_st_name,
                destination_lat=d_st_lat,
                destination_lon=d_st_lon
            ))
            
    elif mode == TransportMode.train:
        from app.models.models import Train
        trains = db.query(Train).filter(
            Train.origin.ilike(f"%{origin_clean}%"),
            Train.destination.ilike(f"%{dest_clean}%")
        ).all()
        for t in trains:
            stops, items = get_transit_stops_and_amenities(t.origin, t.destination, "train", t.train_name, f"train_{t.id}")
            (o_st_name, o_st_lat, o_st_lon), (d_st_name, d_st_lat, d_st_lon) = get_transit_stations(t.origin, t.destination, "train")
            results.append(TransportOption(
                id=f"train_{t.id}",
                origin=t.origin,
                destination=t.destination,
                mode=TransportMode.train,
                operator=t.train_name,
                departure_time=t.departure_time,
                arrival_time=t.arrival_time,
                duration_hrs=t.duration_hrs,
                fare_inr=t.fare_inr,
                seats_available=t.seats_available,
                intermediate_stops=stops,
                complimentary_items=items,
                origin_station_name=o_st_name,
                origin_lat=o_st_lat,
                origin_lon=o_st_lon,
                destination_station_name=d_st_name,
                destination_lat=d_st_lat,
                destination_lon=d_st_lon
            ))
            
    elif mode == TransportMode.flight:
        from app.models.models import Flight
        flights = db.query(Flight).filter(
            Flight.origin.ilike(f"%{origin_clean}%"),
            Flight.destination.ilike(f"%{dest_clean}%")
        ).all()
        for f in flights:
            stops, items = get_transit_stops_and_amenities(f.origin, f.destination, "flight", f.airline, f"flight_{f.id}")
            (o_st_name, o_st_lat, o_st_lon), (d_st_name, d_st_lat, d_st_lon) = get_transit_stations(f.origin, f.destination, "flight")
            results.append(TransportOption(
                id=f"flight_{f.id}",
                origin=f.origin,
                destination=f.destination,
                mode=TransportMode.flight,
                operator=f.airline,
                departure_time=f.departure_time,
                arrival_time=f.arrival_time,
                duration_hrs=f.duration_hrs,
                fare_inr=f.fare_inr,
                seats_available=f.seats_available,
                intermediate_stops=stops,
                complimentary_items=items,
                origin_station_name=o_st_name,
                origin_lat=o_st_lat,
                origin_lon=o_st_lon,
                destination_station_name=d_st_name,
                destination_lat=d_st_lat,
                destination_lon=d_st_lon
            ))
            
    return results


def get_transport_option_by_id(option_id: str, db: Session) -> TransportOption | None:
    """
    Fetch a transport option by its DB-formatted ID (e.g. 'bus_12').
    """
    if not option_id or "_" not in option_id:
        return None
    try:
        parts = option_id.split("_")
        mode = parts[0]
        item_id = int(parts[1])
    except (ValueError, IndexError):
        return None

    if mode == "bus":
        from app.models.models import Bus
        item = db.query(Bus).filter(Bus.id == item_id).first()
        if item:
            stops, items = get_transit_stops_and_amenities(item.origin, item.destination, "bus", item.operator_name, option_id)
            (o_st_name, o_st_lat, o_st_lon), (d_st_name, d_st_lat, d_st_lon) = get_transit_stations(item.origin, item.destination, "bus")
            return TransportOption(
                id=option_id,
                origin=item.origin,
                destination=item.destination,
                mode=TransportMode.bus,
                operator=item.operator_name,
                departure_time=item.departure_time,
                arrival_time=item.arrival_time,
                duration_hrs=item.duration_hrs,
                fare_inr=item.fare_inr,
                seats_available=item.seats_available,
                intermediate_stops=stops,
                complimentary_items=items,
                origin_station_name=o_st_name,
                origin_lat=o_st_lat,
                origin_lon=o_st_lon,
                destination_station_name=d_st_name,
                destination_lat=d_st_lat,
                destination_lon=d_st_lon
            )
    elif mode == "train":
        from app.models.models import Train
        item = db.query(Train).filter(Train.id == item_id).first()
        if item:
            stops, items = get_transit_stops_and_amenities(item.origin, item.destination, "train", item.train_name, option_id)
            (o_st_name, o_st_lat, o_st_lon), (d_st_name, d_st_lat, d_st_lon) = get_transit_stations(item.origin, item.destination, "train")
            return TransportOption(
                id=option_id,
                origin=item.origin,
                destination=item.destination,
                mode=TransportMode.train,
                operator=item.train_name,
                departure_time=item.departure_time,
                arrival_time=item.arrival_time,
                duration_hrs=item.duration_hrs,
                fare_inr=item.fare_inr,
                seats_available=item.seats_available,
                intermediate_stops=stops,
                complimentary_items=items,
                origin_station_name=o_st_name,
                origin_lat=o_st_lat,
                origin_lon=o_st_lon,
                destination_station_name=d_st_name,
                destination_lat=d_st_lat,
                destination_lon=d_st_lon
            )
    elif mode == "flight":
        from app.models.models import Flight
        item = db.query(Flight).filter(Flight.id == item_id).first()
        if item:
            stops, items = get_transit_stops_and_amenities(item.origin, item.destination, "flight", item.airline, option_id)
            (o_st_name, o_st_lat, o_st_lon), (d_st_name, d_st_lat, d_st_lon) = get_transit_stations(item.origin, item.destination, "flight")
            return TransportOption(
                id=option_id,
                origin=item.origin,
                destination=item.destination,
                mode=TransportMode.flight,
                operator=item.airline,
                departure_time=item.departure_time,
                arrival_time=item.arrival_time,
                duration_hrs=item.duration_hrs,
                fare_inr=item.fare_inr,
                seats_available=item.seats_available,
                intermediate_stops=stops,
                complimentary_items=items,
                origin_station_name=o_st_name,
                origin_lat=o_st_lat,
                origin_lon=o_st_lon,
                destination_station_name=d_st_name,
                destination_lat=d_st_lat,
                destination_lon=d_st_lon
            )
    return None


def calculate_total_fare(going_fare: float, include_return: bool, return_fare: float = 0) -> dict:
    """
    Calculate total transport fare.
    """
    total = going_fare + (return_fare if include_return else 0)
    return {
        "going_fare_inr": going_fare,
        "return_fare_inr": return_fare if include_return else 0,
        "total_fare_inr": total,
    }