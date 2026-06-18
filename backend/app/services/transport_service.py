"""
Transport Service
-----------------
Mock data for bus, train and flight options.
Replace with real APIs later:
  Bus    → RedBus API
  Train  → RapidAPI Indian Railways
  Flight → Amadeus API / Skyscanner API
"""

from app.schemas.schemas import TransportOption, TransportMode


# ── Mock Bus Options ──────────────────────────────────────────────────────────

def mock_bus_options(origin: str, destination: str) -> list:
    return [
        TransportOption(
            id="bus_001",
            origin=origin,
            destination=destination,
            mode=TransportMode.bus,
            operator="RSRTC Volvo",
            departure_time="06:00 AM",
            arrival_time="12:00 PM",
            duration_hrs=6.0,
            fare_inr=450,
            seats_available=32,
        ),
        TransportOption(
            id="bus_002",
            origin=origin,
            destination=destination,
            mode=TransportMode.bus,
            operator="Orange Travels",
            departure_time="09:30 AM",
            arrival_time="04:00 PM",
            duration_hrs=6.5,
            fare_inr=380,
            seats_available=18,
        ),
        TransportOption(
            id="bus_003",
            origin=origin,
            destination=destination,
            mode=TransportMode.bus,
            operator="Rajasthan Roadways",
            departure_time="11:00 PM",
            arrival_time="05:30 AM",
            duration_hrs=6.5,
            fare_inr=290,
            seats_available=40,
        ),
    ]


# ── Mock Train Options ────────────────────────────────────────────────────────

def mock_train_options(origin: str, destination: str) -> list:
    return [
        TransportOption(
            id="train_001",
            origin=origin,
            destination=destination,
            mode=TransportMode.train,
            operator="Ajmer Chetak Express",
            departure_time="07:15 AM",
            arrival_time="01:45 PM",
            duration_hrs=6.5,
            fare_inr=320,
            seats_available=120,
        ),
        TransportOption(
            id="train_002",
            origin=origin,
            destination=destination,
            mode=TransportMode.train,
            operator="Mewar Express",
            departure_time="07:00 PM",
            arrival_time="11:30 PM",
            duration_hrs=4.5,
            fare_inr=520,
            seats_available=64,
        ),
        TransportOption(
            id="train_003",
            origin=origin,
            destination=destination,
            mode=TransportMode.train,
            operator="Rajdhani Express",
            departure_time="04:30 PM",
            arrival_time="08:00 PM",
            duration_hrs=3.5,
            fare_inr=850,
            seats_available=28,
        ),
    ]


# ── Mock Flight Options ───────────────────────────────────────────────────────

def mock_flight_options(origin: str, destination: str) -> list:
    return [
        TransportOption(
            id="flight_001",
            origin=origin,
            destination=destination,
            mode=TransportMode.flight,
            operator="IndiGo",
            departure_time="06:00 AM",
            arrival_time="07:10 AM",
            duration_hrs=1.2,
            fare_inr=3200,
            seats_available=45,
        ),
        TransportOption(
            id="flight_002",
            origin=origin,
            destination=destination,
            mode=TransportMode.flight,
            operator="Air India",
            departure_time="11:30 AM",
            arrival_time="12:45 PM",
            duration_hrs=1.25,
            fare_inr=4100,
            seats_available=22,
        ),
        TransportOption(
            id="flight_003",
            origin=origin,
            destination=destination,
            mode=TransportMode.flight,
            operator="SpiceJet",
            departure_time="06:30 PM",
            arrival_time="07:40 PM",
            duration_hrs=1.2,
            fare_inr=2800,
            seats_available=60,
        ),
    ]


# ── Main search function ──────────────────────────────────────────────────────

def search_transport(origin: str, destination: str, mode: str) -> list:
    """
    Main function called by the router.
    Returns mock options based on selected mode.
    Replace inner functions with real API calls in production.
    """
    if mode == TransportMode.bus:
        return mock_bus_options(origin, destination)
    elif mode == TransportMode.train:
        return mock_train_options(origin, destination)
    elif mode == TransportMode.flight:
        return mock_flight_options(origin, destination)
    else:
        return []


def get_transport_option_by_id(option_id: str) -> TransportOption | None:
    if not option_id or "_" not in option_id:
        return None
    mode = option_id.split("_")[0]
    # Fetch from standard mock route Delhi -> Jaipur
    options = search_transport("Delhi", "Jaipur", mode)
    return next((o for o in options if o.id == option_id), None)


# ── Fare calculator ───────────────────────────────────────────────────────────

def calculate_total_fare(
    going_fare: float,
    include_return: bool,
    return_fare: float = 0
) -> dict:
    """
    Calculate total transport fare.
    Return fare is 0 if user does not book return ticket.
    """
    total = going_fare + (return_fare if include_return else 0)
    return {
        "going_fare_inr": going_fare,
        "return_fare_inr": return_fare if include_return else 0,
        "total_fare_inr": total,
    }