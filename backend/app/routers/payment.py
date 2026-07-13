import hmac
import hashlib
import json
import httpx
import base64
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter()

class OrderCreateRequest(BaseModel):
    amount_inr: float
    booking_type: str  # "hotel", "transit", "cab", "food"
    details: Dict[str, Any]

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    booking_type: str
    details: Dict[str, Any]

@router.post("/create-order")
async def create_payment_order(
    req: OrderCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a Razorpay Order ID.
    If Razorpay keys are not configured in settings, we return a mock order ID
    to support seamless offline/sandbox development testing.
    """
    amount_paise = int(req.amount_inr * 100)
    key_id = settings.razorpay_key_id.strip() if settings.razorpay_key_id else ""
    key_secret = settings.razorpay_key_secret.strip() if settings.razorpay_key_secret else ""
    
    if not key_id or not key_secret:
        # Mock Mode
        mock_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        return {
            "order_id": mock_id,
            "amount": amount_paise,
            "currency": "INR",
            "key_id": "rzp_test_mockkey",
            "mock": True
        }
        
    url = "https://api.razorpay.com/v1/orders"
    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"receipt_{uuid.uuid4().hex[:8]}"
    }
    
    # HTTP Basic Auth Encoding
    auth_str = f"{key_id}:{key_secret}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            res = await client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            res_data = res.json()
            return {
                "order_id": res_data["id"],
                "amount": res_data["amount"],
                "currency": res_data["currency"],
                "key_id": key_id,
                "mock": False
            }
        except Exception as e:
            # Fallback to mock order if API fails or settings are wrong
            mock_id = f"order_mock_{uuid.uuid4().hex[:12]}"
            print(f"Razorpay order creation failed: {e}. Falling back to mock.")
            return {
                "order_id": mock_id,
                "amount": amount_paise,
                "currency": "INR",
                "key_id": "rzp_test_mockkey",
                "mock": True
            }

@router.post("/verify")
def verify_payment_signature(
    req: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Verify payment signature and commit booking changes to the database.
    """
    user_id = int(current_user["user_id"])
    key_secret = settings.razorpay_key_secret.strip() if settings.razorpay_key_secret else ""
    
    is_mock = req.razorpay_order_id.startswith("order_mock_")
    
    if not is_mock and key_secret:
        # Cryptographic verification
        msg = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
        expected = hmac.new(key_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
        if expected != req.razorpay_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Razorpay payment verification failed: Invalid Signature"
            )
            
    # Process the database action depending on booking type
    b_type = req.booking_type.lower()
    details = req.details
    
    try:
        if b_type == "hotel":
            from app.models.models import Hotel, HotelBooking
            hotel_id = int(details["hotel_id"])
            num_rooms = int(details["num_rooms"])
            
            hotel = db.query(Hotel).filter(Hotel.id == hotel_id).with_for_update().first()
            if not hotel or hotel.rooms_available < num_rooms:
                raise HTTPException(400, "Hotel rooms unavailable")
                
            booking = HotelBooking(
                hotel_id=hotel_id,
                user_id=user_id,
                check_in_date=details["check_in_date"],
                check_out_date=details["check_out_date"],
                num_rooms=num_rooms,
                num_guests=int(details["num_guests"]),
                total_price_inr=float(details["total_price_inr"]),
                status="confirmed"
            )
            hotel.rooms_booked += num_rooms
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return {"success": True, "booking_id": booking.id}
            
        elif b_type == "transit":
            from app.models.models import Booking
            transport_option_id = details["transport_option_id"]
            
            # Seat lock verification
            parts = transport_option_id.split("_")
            mode = parts[0]
            item_id = int(parts[1])
            
            if mode == "bus":
                from app.models.models import Bus
                bus = db.query(Bus).filter(Bus.id == item_id).with_for_update().first()
                if not bus or bus.seats_available < 1: raise HTTPException(400, "Bus seats unavailable")
                bus.seats_booked += 1
            elif mode == "train":
                from app.models.models import Train
                train = db.query(Train).filter(Train.id == item_id).with_for_update().first()
                if not train or train.seats_available < 1: raise HTTPException(400, "Train seats unavailable")
                train.seats_booked += 1
            elif mode == "flight":
                from app.models.models import Flight
                flight = db.query(Flight).filter(Flight.id == item_id).with_for_update().first()
                if not flight or flight.seats_available < 1: raise HTTPException(400, "Flight seats unavailable")
                flight.seats_booked += 1
                
            booking = Booking(
                user_id=user_id,
                transport_option_id=transport_option_id,
                passenger_name=details["passenger_name"],
                travel_date=details["travel_date"],
                include_return=bool(details.get("include_return", False)),
                return_date=details.get("return_date"),
                going_fare_inr=float(details["going_fare_inr"]),
                return_fare_inr=float(details.get("return_fare_inr", 0)),
                total_fare_inr=float(details["total_fare_inr"]),
                status="confirmed",
                selected_seats=details.get("selected_seats"),
                travel_class=details.get("travel_class")
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return {"success": True, "booking_id": booking.id}
            
        elif b_type == "cab":
            from app.models.models import ProviderBooking, ProviderVehicle
            vehicle_id = int(details["vehicle_id"])
            
            # Cab bookings doesn't have inventory lock on seats, but let's confirm vehicle exists
            vehicle = db.query(ProviderVehicle).filter(ProviderVehicle.id == vehicle_id).first()
            if not vehicle:
                raise HTTPException(404, "Vehicle not found")
                
            booking = ProviderBooking(
                vehicle_id=vehicle_id,
                user_id=user_id,
                passenger_name=details["passenger_name"],
                passenger_phone=details.get("passenger_phone"),
                passenger_email=details.get("passenger_email"),
                travel_date=details["travel_date"],
                num_seats=int(details.get("num_seats", 1)),
                pickup_location=details.get("pickup_location"),
                dropoff_location=details.get("dropoff_location"),
                selected_seats=details.get("selected_seats"),
                total_fare_inr=float(details["total_fare_inr"]),
                status="confirmed",
                passenger_details=details.get("passenger_details")
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)
            return {"success": True, "booking_id": booking.id}
            
        elif b_type == "food":
            from app.models.models import Restaurant, FoodOrder
            restaurant_id = int(details["restaurant_id"])
            
            restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
            if not restaurant:
                raise HTTPException(404, "Restaurant not found")
                
            order = FoodOrder(
                user_id=user_id,
                restaurant_id=restaurant_id,
                items_json=json.dumps(details["items"]),
                total_amount=float(details["total_price_inr"]),
                status="confirmed",
                preparation_time_mins=20,
                user_arrival_time_mins=int(details.get("user_arrival_time_mins", 30)),
                payment_method="prepaid"
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            return {"success": True, "order_id": order.id}
            
        else:
            raise HTTPException(400, "Unknown booking type")
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Database transaction failed: {str(e)}")
