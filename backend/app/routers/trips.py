from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from app.services.trip_chatbot import chat_with_roadbuddy
from typing import Optional
from sqlalchemy.orm import Session
from app.services.waypoint_suggester import suggest_waypoints
from app.schemas.schemas import TripCreate, TripOut, TravelMode
from app.services.ai_planner import generate_itinerary
from app.core.auth import get_current_user
from app.services.route_safety import analyze_route_safety
from app.core.database import get_db
from app.models.models import Trip, TripStop, Vehicle
from app.services.trip_recommender import get_trip_recommendations

router = APIRouter()


@router.post("/generate", response_model=TripOut, status_code=201)
async def create_trip(
    data: TripCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an AI-powered road trip itinerary."""

    if data.travel_mode == TravelMode.own_vehicle:
        if not data.vehicle_id:
            raise HTTPException(
                status_code=400,
                detail="vehicle_id is required for own vehicle mode"
            )
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == int(data.vehicle_id),
            Vehicle.user_id == int(current_user["user_id"])
        ).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        vehicle_info = {
            "fuel_type":    vehicle.fuel_type,
            "category":     vehicle.category,
            "mileage_kmpl": vehicle.mileage_kmpl,
        }
    else:
        vehicle_info = {}

    try:
        trip_out = await generate_itinerary(data, vehicle_info)

        trip = Trip(
            user_id            = int(current_user["user_id"]),
            vehicle_id         = int(data.vehicle_id) if data.vehicle_id else None,
            origin             = data.origin,
            destination        = data.destination,
            origin_lat         = data.origin_lat,
            origin_lon         = data.origin_lon,
            destination_lat    = data.destination_lat,
            destination_lon    = data.destination_lon,
            start_date         = data.start_date,
            end_date           = data.end_date,
            budget_inr         = data.budget_inr,
            travel_mode        = data.travel_mode,
            group_type         = data.group_type,
            num_people         = data.num_people,
            fuel_cost_inr      = trip_out.fuel_cost_inr,
            toll_cost_inr      = trip_out.toll_cost_inr,
            transport_fare_inr = trip_out.transport_fare_inr,
            return_fare_inr    = trip_out.return_fare_inr,
            hotel_cost_inr     = trip_out.hotel_cost_inr,
            food_cost_inr      = trip_out.food_cost_inr,
            total_cost_inr     = trip_out.total_estimated_cost_inr,
            ai_summary         = trip_out.ai_summary,
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)

        for stop in trip_out.stops:
            db_stop = TripStop(
                trip_id    = trip.id,
                day        = stop.day,
                time_slot  = stop.time_slot,
                place_name = stop.place_name,
                place_type = stop.place_type,
            )
            db.add(db_stop)
        db.commit()

        trip_out.id = str(trip.id)
        trip_out.start_date = trip.start_date
        trip_out.end_date = trip.end_date
        trip_out.group_type = trip.group_type
        trip_out.num_people = trip.num_people
        trip_out.budget_inr = trip.budget_inr
        trip_out.origin_lat = trip.origin_lat
        trip_out.origin_lon = trip.origin_lon
        trip_out.destination_lat = trip.destination_lat
        trip_out.destination_lon = trip.destination_lon
        return trip_out

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my", response_model=list[TripOut])
def list_my_trips(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all trips for the logged-in user."""
    trips = db.query(Trip).filter(
        Trip.user_id == int(current_user["user_id"])
    ).all()

    return [
        TripOut(
            id                       = str(t.id),
            origin                   = t.origin,
            destination              = t.destination,
            origin_lat               = t.origin_lat,
            origin_lon               = t.origin_lon,
            destination_lat          = t.destination_lat,
            destination_lon          = t.destination_lon,
            travel_mode              = t.travel_mode,
            total_distance_km        = 0,
            stops                    = [],
            fuel_cost_inr            = t.fuel_cost_inr,
            toll_cost_inr            = t.toll_cost_inr,
            transport_fare_inr       = t.transport_fare_inr,
            return_fare_inr          = t.return_fare_inr,
            hotel_cost_inr           = t.hotel_cost_inr,
            food_cost_inr            = t.food_cost_inr,
            total_estimated_cost_inr = t.total_cost_inr,
            ai_summary               = t.ai_summary or "",
            start_date               = t.start_date,
            end_date                 = t.end_date,
            group_type               = t.group_type,
            num_people               = t.num_people,
            budget_inr               = t.budget_inr,
        )
        for t in trips
    ]


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single trip with all stops."""
    trip = db.query(Trip).filter(
        Trip.id == int(trip_id),
        Trip.user_id == int(current_user["user_id"])
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    stops = db.query(TripStop).filter(TripStop.trip_id == trip.id).all()

    from app.schemas.schemas import ItineraryStop
    stop_list = [
        ItineraryStop(
            day         = s.day,
            time_slot   = s.time_slot,
            place_name  = s.place_name,
            place_type  = s.place_type,
            description = "",
        )
        for s in stops
    ]

    return TripOut(
        id                       = str(trip.id),
        origin                   = trip.origin,
        destination              = trip.destination,
        origin_lat               = trip.origin_lat,
        origin_lon               = trip.origin_lon,
        destination_lat          = trip.destination_lat,
        destination_lon          = trip.destination_lon,
        travel_mode              = trip.travel_mode,
        total_distance_km        = 0,
        stops                    = stop_list,
        fuel_cost_inr            = trip.fuel_cost_inr,
        toll_cost_inr            = trip.toll_cost_inr,
        transport_fare_inr       = trip.transport_fare_inr,
        return_fare_inr          = trip.return_fare_inr,
        hotel_cost_inr           = trip.hotel_cost_inr,
        food_cost_inr            = trip.food_cost_inr,
        total_estimated_cost_inr = trip.total_cost_inr,
        ai_summary               = trip.ai_summary or "",
        start_date               = trip.start_date,
        end_date                 = trip.end_date,
        group_type               = trip.group_type,
        num_people               = trip.num_people,
        budget_inr               = trip.budget_inr,
    )


@router.put("/{trip_id}", response_model=TripOut)
async def update_trip(
    trip_id: str,
    data: TripCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing trip and regenerate its itinerary."""
    trip = db.query(Trip).filter(
        Trip.id == int(trip_id),
        Trip.user_id == int(current_user["user_id"])
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if data.travel_mode == TravelMode.own_vehicle:
        if not data.vehicle_id:
            raise HTTPException(
                status_code=400,
                detail="vehicle_id is required for own vehicle mode"
            )
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == int(data.vehicle_id),
            Vehicle.user_id == int(current_user["user_id"])
        ).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        vehicle_info = {
            "fuel_type":    vehicle.fuel_type,
            "category":     vehicle.category,
            "mileage_kmpl": vehicle.mileage_kmpl,
        }
    else:
        vehicle_info = {}

    try:
        trip_out = await generate_itinerary(data, vehicle_info)

        # Update trip fields
        trip.vehicle_id         = int(data.vehicle_id) if data.vehicle_id else None
        trip.origin             = data.origin
        trip.destination        = data.destination
        trip.origin_lat         = data.origin_lat
        trip.origin_lon         = data.origin_lon
        trip.destination_lat    = data.destination_lat
        trip.destination_lon    = data.destination_lon
        trip.start_date         = data.start_date
        trip.end_date           = data.end_date
        trip.budget_inr         = data.budget_inr
        trip.travel_mode        = data.travel_mode.value if hasattr(data.travel_mode, 'value') else data.travel_mode
        trip.group_type         = data.group_type.value if hasattr(data.group_type, 'value') else data.group_type
        trip.num_people         = data.num_people
        trip.fuel_cost_inr      = trip_out.fuel_cost_inr
        trip.toll_cost_inr      = trip_out.toll_cost_inr
        trip.transport_fare_inr = trip_out.transport_fare_inr
        trip.return_fare_inr    = trip_out.return_fare_inr
        trip.hotel_cost_inr     = trip_out.hotel_cost_inr
        trip.food_cost_inr      = trip_out.food_cost_inr
        trip.total_cost_inr     = trip_out.total_estimated_cost_inr
        trip.ai_summary         = trip_out.ai_summary

        # Clear old stops
        db.query(TripStop).filter(TripStop.trip_id == trip.id).delete()

        # Add new stops
        for stop in trip_out.stops:
            db_stop = TripStop(
                trip_id    = trip.id,
                day        = stop.day,
                time_slot  = stop.time_slot,
                place_name = stop.place_name,
                place_type = stop.place_type,
            )
            db.add(db_stop)
        
        db.commit()
        db.refresh(trip)

        trip_out.id = str(trip.id)
        trip_out.start_date = trip.start_date
        trip_out.end_date = trip.end_date
        trip_out.group_type = trip.group_type
        trip_out.num_people = trip.num_people
        trip_out.budget_inr = trip.budget_inr
        trip_out.origin_lat = trip.origin_lat
        trip_out.origin_lon = trip.origin_lon
        trip_out.destination_lat = trip.destination_lat
        trip_out.destination_lon = trip.destination_lon
        return trip_out
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trip_id}/cost")
def get_trip_cost(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full cost breakdown for a trip."""
    trip = db.query(Trip).filter(
        Trip.id == int(trip_id),
        Trip.user_id == int(current_user["user_id"])
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.travel_mode == TravelMode.own_vehicle:
        return {
            "trip_id":     trip_id,
            "travel_mode": trip.travel_mode,
            "breakdown": {
                "fuel_cost_inr":  trip.fuel_cost_inr,
                "toll_cost_inr":  trip.toll_cost_inr,
                "hotel_cost_inr": trip.hotel_cost_inr,
                "food_cost_inr":  trip.food_cost_inr,
            },
            "grand_total_inr": trip.total_cost_inr,
        }
    else:
        return {
            "trip_id":     trip_id,
            "travel_mode": trip.travel_mode,
            "breakdown": {
                "going_fare_inr":  trip.transport_fare_inr,
                "return_fare_inr": trip.return_fare_inr,
                "hotel_cost_inr":  trip.hotel_cost_inr,
                "food_cost_inr":   trip.food_cost_inr,
            },
            "grand_total_inr": trip.total_cost_inr,
        }


@router.delete("/{trip_id}", status_code=204)
def delete_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a trip and all its stops."""
    trip = db.query(Trip).filter(
        Trip.id == int(trip_id),
        Trip.user_id == int(current_user["user_id"])
    ).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    db.query(TripStop).filter(TripStop.trip_id == trip.id).delete()
    db.delete(trip)
    db.commit()



class WaypointRequest(BaseModel):
    origin: str
    destination: str
    preferences: Optional[list[str]] = []
    travel_mode: Optional[str] = "own_vehicle"
    num_people: Optional[int] = 2
    group_type: Optional[str] = "friends"


@router.post("/suggest-waypoints")
async def get_waypoint_suggestions(request: WaypointRequest):
    """
    AI-powered waypoint suggestions between origin and destination.
    Returns hidden gems, dhabas, viewpoints, and must-visit stops.
    """
    try:
        result = await suggest_waypoints(
            origin=request.origin,
            destination=request.destination,
            preferences=request.preferences,
            travel_mode=request.travel_mode,
            num_people=request.num_people,
            group_type=request.group_type,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))




def get_optional_user(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header:
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = auth_header
    else:
        token = request.cookies.get("access_token")
        
    if not token:
        return None
        
    try:
        from jose import jwt
        from app.core.config import settings
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if user_id:
            return {"user_id": user_id}
    except Exception:
        pass
    return None


def build_user_context(user_id: int, db: Session) -> str:
    from app.models.models import User, Vehicle, Trip, Booking, HotelBooking, TrainBooking, BusBooking, FlightBooking, ProviderBooking
    from app.services.transport_service import get_transport_option_by_id, get_transit_stops_and_amenities
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return ""
        
    lines = []
    lines.append(f"User Name: {user.name}")
    lines.append(f"User Email: {user.email}")
    
    # Vehicles
    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user_id).all()
    if vehicles:
        lines.append("User Vehicles:")
        for v in vehicles:
            lines.append(f"- Vehicle: {v.name} ({v.category}, Fuel: {v.fuel_type}, Mileage: {v.mileage_kmpl} kmpl)")
            
    # Trips
    trips = db.query(Trip).filter(Trip.user_id == user_id).all()
    if trips:
        lines.append("User Trips:")
        for t in trips:
            lines.append(f"- Trip: {t.origin} to {t.destination} ({t.start_date} to {t.end_date or 'N/A'}), Travel Mode: {t.travel_mode}, Budget: INR {t.budget_inr}, Total Estimated Cost: INR {t.total_cost_inr}")

    # Hotel Bookings
    hotel_bookings = db.query(HotelBooking).filter(HotelBooking.user_id == user_id).all()
    if hotel_bookings:
        lines.append("User Hotel Bookings:")
        for hb in hotel_bookings:
            hotel_name = hb.hotel.name if (hb.hotel) else "Hotel"
            hotel_city = hb.hotel.city if (hb.hotel) else "Unknown"
            hotel_amenities = hb.hotel.amenities if (hb.hotel and hb.hotel.amenities) else "WiFi, AC"
            comp_list = ["Complimentary Welcome Drink"]
            if "restaurant" in hotel_amenities.lower() or "breakfast" in hotel_amenities.lower() or "pool" in hotel_amenities.lower():
                comp_list.append("Complimentary Buffet Breakfast")
            comp_str = ", ".join(comp_list)
            lines.append(
                f"- Hotel Booking: {hotel_name} in {hotel_city}. Check-in: {hb.check_in_date}, Check-out: {hb.check_out_date}. Rooms: {hb.num_rooms}, Guests: {hb.num_guests}. Status: {hb.status}. Price: INR {hb.total_price_inr}. Included Amenities: {hotel_amenities}. Complimentary Inclusions: {comp_str}."
            )
            
    # Train Bookings
    train_bookings = db.query(TrainBooking).filter(TrainBooking.user_id == user_id).all()
    if train_bookings:
        lines.append("User Train Bookings:")
        for tb in train_bookings:
            train_name = tb.train.train_name if (tb.train) else "Train"
            train_num = tb.train.train_number if (tb.train) else "N/A"
            origin = tb.train.origin if (tb.train) else "N/A"
            destination = tb.train.destination if (tb.train) else "N/A"
            stops, items = get_transit_stops_and_amenities(origin, destination, "train", train_name)
            stops_str = ", ".join([f"{s['name']} (stop for {s['duration_mins']} mins)" for s in stops]) if stops else "Direct (no stops)"
            items_str = ", ".join(items) if items else "Standard amenities"
            lines.append(
                f"- Train Booking: {train_name} ({train_num}) from {origin} to {destination}. Travel Date: {tb.travel_date}. Passenger: {tb.passenger_name}, Seats: {tb.num_seats}. Status: {tb.status}. Fare: INR {tb.total_fare_inr}. Intermediate Stops: {stops_str}. Complimentary Inclusions: {items_str}."
            )
            
    # Bus Bookings
    bus_bookings = db.query(BusBooking).filter(BusBooking.user_id == user_id).all()
    if bus_bookings:
        lines.append("User Bus Bookings:")
        for bb in bus_bookings:
            operator = bb.bus.operator_name if (bb.bus) else "Bus Operator"
            bus_type = bb.bus.bus_type if (bb.bus) else "AC"
            origin = bb.bus.origin if (bb.bus) else "N/A"
            destination = bb.bus.destination if (bb.bus) else "N/A"
            stops, items = get_transit_stops_and_amenities(origin, destination, "bus", operator)
            stops_str = ", ".join([f"{s['name']} (stop for {s['duration_mins']} mins)" for s in stops]) if stops else "Direct (no stops)"
            items_str = ", ".join(items) if items else "Standard amenities"
            lines.append(
                f"- Bus Booking: Bus with {operator} ({bus_type}) from {origin} to {destination}. Travel Date: {bb.travel_date}. Passenger: {bb.passenger_name}, Seats: {bb.num_seats}. Status: {bb.status}. Fare: INR {bb.total_fare_inr}. Intermediate Stops: {stops_str}. Complimentary Inclusions: {items_str}."
            )
            
    # Flight Bookings
    flight_bookings = db.query(FlightBooking).filter(FlightBooking.user_id == user_id).all()
    if flight_bookings:
        lines.append("User Flight Bookings:")
        for fb in flight_bookings:
            airline = fb.flight.airline if (fb.flight) else "Airline"
            flight_num = fb.flight.flight_number if (fb.flight) else "N/A"
            origin = fb.flight.origin if (fb.flight) else "N/A"
            destination = fb.flight.destination if (fb.flight) else "N/A"
            stops, items = get_transit_stops_and_amenities(origin, destination, "flight", airline)
            stops_str = ", ".join([f"{s['name']} (stop for {s['duration_mins']} mins)" for s in stops]) if stops else "Direct (no stops)"
            items_str = ", ".join(items) if items else "Standard amenities"
            lines.append(
                f"- Flight Booking: {airline} ({flight_num}) from {origin} to {destination}. Travel Date: {fb.travel_date}. Passenger: {fb.passenger_name}, Seats: {fb.num_seats}. Status: {fb.status}. Fare: INR {fb.total_fare_inr}. Intermediate Stops: {stops_str}. Complimentary Inclusions: {items_str}."
            )
            
    # Transit Bookings (generic Booking model)
    transit_bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    if transit_bookings:
        lines.append("User Transit Bookings:")
        for b in transit_bookings:
            opt = get_transport_option_by_id(b.transport_option_id, db)
            mode = "Transit"
            operator = "Unknown"
            origin = "N/A"
            destination = "N/A"
            stops_str = "Direct (no stops)"
            items_str = "Standard amenities"
            if opt:
                mode = opt.mode
                operator = opt.operator
                origin = opt.origin
                destination = opt.destination
                stops, items = get_transit_stops_and_amenities(opt.origin, opt.destination, opt.mode, opt.operator)
                stops_str = ", ".join([f"{s['name']} (stop for {s['duration_mins']} mins)" for s in stops]) if stops else "Direct (no stops)"
                items_str = ", ".join(items) if items else "Standard amenities"
            else:
                try:
                    mode = b.transport_option_id.split("_")[0]
                except Exception:
                    pass
            lines.append(
                f"- Transit Booking: {mode.capitalize()} with {operator} from {origin} to {destination}. Travel Date: {b.travel_date}. Passenger: {b.passenger_name}, Fare: INR {b.total_fare_inr}. Status: {b.status}. Intermediate Stops: {stops_str}. Complimentary Inclusions: {items_str}."
            )

    # Cab Bookings (ProviderBooking)
    cab_bookings = db.query(ProviderBooking).filter(ProviderBooking.user_id == user_id).all()
    if cab_bookings:
        lines.append("User Cab Bookings:")
        for cb in cab_bookings:
            v_name = cb.vehicle.vehicle_name if (cb.vehicle) else "Cab"
            provider_name = cb.vehicle.provider.company_name if (cb.vehicle and cb.vehicle.provider) else "Cab Provider"
            p_loc = cb.pickup_location or "N/A"
            d_loc = cb.dropoff_location or "N/A"
            p_name = p_loc.split("|||")[0] if "|||" in p_loc else p_loc
            d_name = d_loc.split("|||")[0] if "|||" in d_loc else d_loc
            stops, items = get_transit_stops_and_amenities(p_name, d_name, "cab", v_name)
            stops_str = ", ".join([f"{s['name']} (stop for {s['duration_mins']} mins)" for s in stops]) if stops else "Direct (no stops)"
            items_str = ", ".join(items) if items else "Standard amenities"
            lines.append(
                f"- Cab Booking: {v_name} with {provider_name} from {p_name} to {d_name}. Travel Date: {cb.travel_date}. Passenger: {cb.passenger_name}, Seats: {cb.num_seats}. Status: {cb.status}. Fare: INR {cb.total_fare_inr}. Intermediate Stops: {stops_str}. Complimentary Inclusions: {items_str}."
            )

    return "\n".join(lines)


class ChatMessage(BaseModel):
    message: str
    history: Optional[list[dict]] = []


@router.post("/chat")
async def trip_chat(
    request: Request,
    body: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    AI-powered conversational trip planning chatbot.
    Supports multi-turn conversation with history.
    """
    try:
        print(f"[CHAT DEBUG] Headers: {dict(request.headers)}")
        print(f"[CHAT DEBUG] Cookies: {dict(request.cookies)}")
        
        user_context = None
        opt_user = get_optional_user(request)
        print(f"[CHAT DEBUG] Resolved opt_user: {opt_user}")
        
        if opt_user:
            user_context = build_user_context(int(opt_user["user_id"]), db)
            print(f"[CHAT DEBUG] Compiled context size: {len(user_context)} characters")
            
        result = await chat_with_roadbuddy(
            message=body.message,
            history=body.history,
            user_context=user_context,
            db=db,
        )
        return result
    except RuntimeError as e:
        print(f"[CHAT DEBUG] Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
class SafetyCheckRequest(BaseModel):
    origin: str
    destination: str
    travel_date: str
    departure_time: Optional[str] = "08:00"
    vehicle_type: Optional[str] = "car"
    num_people: Optional[int] = 2


@router.post("/safety-check")
async def check_route_safety(request: SafetyCheckRequest):
    """
    AI-powered route safety analyzer.
    Flags dangerous stretches, seasonal hazards and gives safety score.
    """
    try:
        result = await analyze_route_safety(
            origin=request.origin,
            destination=request.destination,
            travel_date=request.travel_date,
            departure_time=request.departure_time,
            vehicle_type=request.vehicle_type,
            num_people=request.num_people,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
class RecommendationRequest(BaseModel):
    home_city: str
    budget_inr: float
    group_type: Optional[str] = "friends"
    num_people: Optional[int] = 2
    duration_days: Optional[int] = 3
    season: Optional[str] = "winter"
    interests: Optional[list[str]] = ["sightseeing"]


@router.post("/recommendations")
async def trip_recommendations(request: RecommendationRequest):
    """
    AI-powered personalized trip recommendations.
    Suggests 5 trips based on budget, group type, season and interests.
    """
    try:
        result = await get_trip_recommendations(
            home_city=request.home_city,
            budget_inr=request.budget_inr,
            group_type=request.group_type,
            num_people=request.num_people,
            duration_days=request.duration_days,
            season=request.season,
            interests=request.interests,
        )
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))