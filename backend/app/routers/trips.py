from fastapi import APIRouter, HTTPException, Depends
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
            start_date         = data.start_date,
            budget_inr         = data.budget_inr,
            travel_mode        = data.travel_mode,
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
    )


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




class ChatMessage(BaseModel):
    message: str
    history: Optional[list[dict]] = []


@router.post("/chat")
async def trip_chat(request: ChatMessage):
    """
    AI-powered conversational trip planning chatbot.
    Supports multi-turn conversation with history.
    """
    try:
        result = await chat_with_roadbuddy(
            message=request.message,
            history=request.history,
        )
        return result
    except RuntimeError as e:
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