import hmac
import hashlib
import json
import httpx
import base64
import uuid
import zlib
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.config import settings
from pydantic import BaseModel
from app.services import duffel_client

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
async def verify_payment_signature(
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
            from app.models.models import Hotel, HotelBooking, User
            hotel_id_raw = str(details["hotel_id"])
            num_rooms = int(details["num_rooms"])
            
            # Fetch user details for Stays booking
            db_user = db.query(User).filter(User.id == user_id).first()
            user_name = db_user.name if db_user else "Traveler"
            user_email = db_user.email if db_user else "traveler@example.com"
            user_phone = getattr(db_user, "phone", None) or "+919999999999"
            
            if hotel_id_raw.startswith("duffel_stay_"):
                # Real Duffel Stays booking!
                search_result_id = hotel_id_raw.replace("duffel_stay_", "")
                guest_details = {
                    "passenger_name": user_name,
                    "passenger_email": user_email,
                    "passenger_phone": user_phone
                }
                
                try:
                    duffel_booking = await duffel_client.book_hotel(
                        search_result_id=search_result_id,
                        guest_details=guest_details,
                        amount=float(details["total_price_inr"])
                    )
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Duffel Stays Booking Failed: {str(e)}")
                
                # Retrieve accommodation properties to insert locally
                accommodation = duffel_booking.get("accommodation", {})
                acc_id = accommodation.get("id") or "acc_placeholder"
                hotel_name = accommodation.get("name", "Luxury Stay")
                hotel_city = accommodation.get("location", {}).get("city", {}).get("name", "City")
                hotel_address = accommodation.get("location", {}).get("address", "Address")
                hotel_rating = float(accommodation.get("rating", 4.0))
                
                # Deterministic integer hash of the accommodation ID
                local_hotel_id = zlib.adler32(acc_id.encode()) & 0x7fffffff
                
                # Insert hotel locally if not exists
                db_hotel = db.query(Hotel).filter(Hotel.id == local_hotel_id).first()
                if not db_hotel:
                    db_hotel = Hotel(
                        id=local_hotel_id,
                        name=hotel_name,
                        city=hotel_city,
                        address=hotel_address,
                        star_rating=hotel_rating,
                        price_per_night_inr=float(details["total_price_inr"]) / (max(int(details["num_rooms"]), 1)),
                        total_rooms=10,
                        rooms_booked=0,
                        amenities="Wi-Fi, AC, Parking, Room Service"
                    )
                    db.add(db_hotel)
                    db.commit()
                
                # Create local HotelBooking linked to local_hotel_id
                booking = HotelBooking(
                    hotel_id=local_hotel_id,
                    user_id=user_id,
                    check_in_date=details["check_in_date"],
                    check_out_date=details["check_out_date"],
                    num_rooms=num_rooms,
                    num_guests=int(details["num_guests"]),
                    total_price_inr=float(details["total_price_inr"]),
                    status="confirmed",
                    duffel_booking_id=duffel_booking.get("id")
                )
                db.add(booking)
                db.commit()
                db.refresh(booking)
                return {"success": True, "booking_id": booking.id}
            else:
                # Local Mock Stay
                hotel_id = int(details["hotel_id"])
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
            from app.models.models import Booking, User
            transport_option_id = str(details["transport_option_id"])
            
            if transport_option_id.startswith("flight_off_"):
                # Real Duffel Flight booking!
                offer_id = transport_option_id.replace("flight_", "")
                
                # Split seats to count travelers
                seats = details.get("selected_seats", "").split(",")
                num_seats = max(len([s for s in seats if s.strip()]), 1)
                
                # Fetch user details
                db_user = db.query(User).filter(User.id == user_id).first()
                user_name = db_user.name if db_user else "Traveler"
                user_email = db_user.email if db_user else "traveler@example.com"
                user_phone = getattr(db_user, "phone", None) or "+919999999999"
                
                passengers = []
                lead_name = details.get("passenger_name") or user_name
                for i in range(num_seats):
                    name = lead_name if i == 0 else f"{lead_name} Traveler {i+1}"
                    passengers.append({
                        "name": name,
                        "age": 30,
                        "email": user_email,
                        "phone": user_phone
                    })
                    
                try:
                    duffel_order = await duffel_client.create_flight_order(
                        offer_id=offer_id,
                        passenger_details=passengers,
                        amount=float(details["total_fare_inr"])
                    )
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Duffel Flight Booking Failed: {str(e)}")
                
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
                    travel_class=details.get("travel_class"),
                    duffel_order_id=duffel_order.get("id")
                )
                db.add(booking)
                db.commit()
                db.refresh(booking)
                return {"success": True, "booking_id": booking.id}
            else:
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


class OTPVerifyRequest(BaseModel):
    otp: str


@router.post("/send-otp")
async def send_payment_otp(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from app.models.models import User
    from app.core.email_otp import generate_and_send_otp, _otp_store
    
    user_id = int(current_user["user_id"])
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    email = db_user.email
    name = db_user.name or "User"
    phone = getattr(db_user, "phone", None) or "Not Registered"
    
    if not email:
        raise HTTPException(status_code=400, detail="User email not found")
        
    try:
        sent = generate_and_send_otp(email, name, otp_type="payment")
        stored = _otp_store.get(email, {})
        otp = stored.get("otp", "")
        
        # Format registered info for display
        masked_email = email
        if "@" in email:
            parts = email.split("@")
            masked_email = f"{parts[0][:3]}***@{parts[1]}"
            
        masked_phone = phone
        if len(phone) >= 10:
            masked_phone = f"+91 ******{phone[-4:]}"
            
        print(f"\n[Payment OTP] Sent OTP '{otp}' to registered email: {email} (Phone: {phone})\n")
        
        return {
            "success": True,
            "email": masked_email,
            "phone": masked_phone,
            "sent_via_email": sent,
            "otp_preview": otp if not sent else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-otp")
async def verify_payment_otp(
    req: OTPVerifyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from app.models.models import User
    from app.core.email_otp import verify_otp, clear_otp
    
    user_id = int(current_user["user_id"])
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    email = db_user.email
    if not email:
        raise HTTPException(status_code=400, detail="User email not found")
        
    is_valid = verify_otp(email, req.otp)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    clear_otp(email)
    return {"success": True}

