"""
AI Partner Helper Chatbot Service — RoadBuddy Partner (Groq)
"""

import httpx
from app.core.config import settings
from sqlalchemy.orm import Session

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are RoadBuddy Partner Assistant, a helpful AI guide for transport operators, fleet managers, and cab/bus service providers on the RoadBuddy platform.
Your job is to help partners manage their vehicles, check user bookings, monitor stats/revenue, and configure settings.

Strict Constraints:
- You must ONLY answer questions directly related to the RoadBuddy Partner dashboard, partner services, and features (e.g., listing vehicles, checking bookings, active passengers, checking revenue, settings).
- If the user asks about ANY other topic (such as general knowledge, coding, tourist itinerary, hotel lists for riders, cooking, history, general questions, etc.), you MUST refuse to answer and respond EXACTLY with:
"I can only answer questions related to our app."
- Keep responses friendly, under 180 words, and use 1-2 emojis."""


def get_provider_data_summary(provider_id: int, db: Session) -> str:
    from app.models.models import ProviderVehicle, ProviderBooking, Provider
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        return "No partner account found."
        
    vehicles = db.query(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
    bookings = db.query(ProviderBooking).join(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
    
    vehicle_summary = []
    for v in vehicles:
        status = "Active" if v.is_active else "Inactive"
        fare_parts = []
        if v.fixed_fare_inr:
            fare_parts.append(f"Fixed Fare: ₹{int(v.fixed_fare_inr)}")
        if v.price_per_km_inr:
            fare_parts.append(f"Price: ₹{v.price_per_km_inr}/km")
        fare_str = " / ".join(fare_parts) if fare_parts else "N/A"
        
        time_parts = []
        if v.departure_time:
            time_parts.append(f"Departs: {v.departure_time}")
        if v.arrival_time:
            time_parts.append(f"Arrives: {v.arrival_time}")
        time_str = " · ".join(time_parts) if time_parts else "N/A"

        vehicle_summary.append(
            f"- {v.vehicle_name} ({v.vehicle_type.upper()}): {v.origin} to {v.destination}, "
            f"Seats: {v.seats_booked}/{v.total_seats} booked, "
            f"Fare: {fare_str}, Timing: {time_str}, Status: {status}, ID: {v.id}"
        )
    
    booking_summary = []
    total_rev = 0.0
    active_booking_count = 0
    for b in bookings:
        if b.status != "cancelled":
            total_rev += b.total_fare_inr
            active_booking_count += 1
        booking_summary.append(
            f"- Booking #{b.id}: Passenger: {b.passenger_name}, Phone: {b.passenger_phone}, "
            f"Email: {b.passenger_email}, Date: {b.travel_date}, Seats: {b.selected_seats or b.num_seats}, "
            f"Fare: ₹{b.total_fare_inr}, Status: {b.status}, Vehicle ID: {b.vehicle_id}"
        )
        
    summary = f"""
Current Partner Context:
- Company Name: {provider.company_name or 'N/A'}
- Contact Person: {provider.contact_person or 'N/A'}
- Total Listed Vehicles: {len(vehicles)}
- Total Bookings: {len(bookings)} (Active: {active_booking_count})
- Total Revenue: ₹{total_rev:,.0f}

Vehicles List:
{chr(10).join(vehicle_summary) if vehicle_summary else "No vehicles listed."}

Bookings List:
{chr(10).join(booking_summary) if booking_summary else "No bookings found."}
"""
    return summary


def mock_partner_chat_response(message: str, provider_id: int = None, db: Session = None) -> str:
    msg_lower = message.lower()

    # ── Early exit: explicitly handle booking queries before any other logic ──
    if db and provider_id and any(phrase in msg_lower for phrase in [
        "what are my booking", "my bookings", "show my booking", "list my booking",
        "display my booking", "show booking", "list booking"
    ]):
        from app.models.models import ProviderVehicle, ProviderBooking
        bookings = db.query(ProviderBooking).join(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
        if not bookings:
            return "📋 You don't have any bookings yet."
        active_bookings = [b for b in bookings if b.status != "cancelled"]
        if not active_bookings:
            return "📋 All your bookings are currently cancelled or inactive."
        lines = []
        for b in active_bookings:
            lines.append(
                f"• **Booking #{b.id}** by {b.passenger_name} | {b.travel_date} | "
                f"Seats: {b.selected_seats or b.num_seats} | Fare: ₹{b.total_fare_inr} | "
                f"Phone: {b.passenger_phone or 'N/A'}"
            )
        return f"📋 You have {len(active_bookings)} active booking(s):\n" + "\n".join(lines)

    # ── Early exit: explicitly handle "show/list my vehicles" before any other logic ──
    if db and provider_id and any(phrase in msg_lower for phrase in [
        "show my vehicle", "list my vehicle", "my vehicles", "show vehicle",
        "list vehicle", "display my vehicle", "display vehicle"
    ]):
        from app.models.models import ProviderVehicle
        vehicles = db.query(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
        if not vehicles:
            return "🚙 You have no vehicles listed yet. Would you like me to guide you on how to add one?"
        lines = []
        for v in vehicles:
            fare_parts = []
            if v.fixed_fare_inr:
                fare_parts.append(f"Fixed Fare: ₹{int(v.fixed_fare_inr)}")
            if v.price_per_km_inr:
                fare_parts.append(f"Price: ₹{v.price_per_km_inr}/km")
            fare_str = " / ".join(fare_parts) if fare_parts else "N/A"
            time_parts = []
            if v.departure_time:
                time_parts.append(f"Departs: {v.departure_time}")
            if v.arrival_time:
                time_parts.append(f"Arrives: {v.arrival_time}")
            time_str = " · ".join(time_parts) if time_parts else "N/A"
            lines.append(
                f"• **{v.vehicle_name}** ({v.vehicle_type.upper()})\n"
                f"  - Route: {v.origin} → {v.destination}\n"
                f"  - Fare: {fare_str}\n"
                f"  - Timing: {time_str}\n"
                f"  - Seats: {v.seats_available}/{v.total_seats} available\n"
                f"  - Status: {'Active' if v.is_active else 'Inactive'}"
            )
        return "🚗 Here are your vehicles:\n" + "\n".join(lines)

    # Check if they are asking about their actual data (vs asking how to do something)
    is_asking_guidance = any(word in msg_lower for word in [
        "how", "guide", "steps", "where do", "instruct", "tutorial", "process",
        "show", "list", "display", "what are"
    ])
    is_asking_data = not is_asking_guidance

    if db and provider_id and is_asking_data:
        from app.models.models import ProviderVehicle, ProviderBooking

        # If they ask about vehicle details, per seat fare, or running times specifically
        is_asking_vehicle_info = ("vehicle" in msg_lower or "car" in msg_lower or "bus" in msg_lower or
                                 any(word in msg_lower for word in ["fare", "price", "time", "running", "cost", "km", "departs", "arrives", "timing"]))

        if is_asking_vehicle_info:
            vehicles = db.query(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
            if not vehicles:
                return "🚙 You have no vehicles listed yet. Would you like me to guide you on how to add one?"
            lines = []
            for v in vehicles:
                fare_parts = []
                if v.fixed_fare_inr:
                    fare_parts.append(f"Fixed Fare: ₹{int(v.fixed_fare_inr)}")
                if v.price_per_km_inr:
                    fare_parts.append(f"Price: ₹{v.price_per_km_inr}/km")
                fare_str = " / ".join(fare_parts) if fare_parts else "N/A"

                time_parts = []
                if v.departure_time:
                    time_parts.append(f"Departs: {v.departure_time}")
                if v.arrival_time:
                    time_parts.append(f"Arrives: {v.arrival_time}")
                time_str = " · ".join(time_parts) if time_parts else "N/A"

                lines.append(
                    f"• **{v.vehicle_name}** ({v.vehicle_type.upper()})\n"
                    f"  - Route: {v.origin} → {v.destination}\n"
                    f"  - Fare Details: {fare_str}\n"
                    f"  - Running Time/Timings: {time_str}\n"
                    f"  - Seats: {v.seats_available}/{v.total_seats} available\n"
                    f"  - Status: {'Active' if v.is_active else 'Inactive'}"
                )
            return "🚗 Here is your vehicle information:\n" + "\n".join(lines)

        elif "booking" in msg_lower or "passenger" in msg_lower or "seat" in msg_lower:
            bookings = db.query(ProviderBooking).join(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
            if not bookings:
                return "📋 You don't have any bookings yet."
            lines = []
            active_bookings = [b for b in bookings if b.status != "cancelled"]
            if not active_bookings:
                return "📋 All your bookings are currently cancelled or inactive."
            for b in active_bookings:
                lines.append(f"• **Booking #{b.id}** by {b.passenger_name} | {b.travel_date} | Seats: {b.selected_seats or b.num_seats} | Fare: ₹{b.total_fare_inr} | Phone: {b.passenger_phone or 'N/A'}")
            return f"📋 You have {len(active_bookings)} active booking(s):\n" + "\n".join(lines)

        elif "revenue" in msg_lower or "money" in msg_lower or "earning" in msg_lower:
            bookings = db.query(ProviderBooking).join(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
            total_rev = sum(b.total_fare_inr for b in bookings if b.status != "cancelled")
            return f"💰 Your total revenue from active bookings is **₹{total_rev:,.2f}**."


    # Fallback to general guidance
    if "vehicle" in msg_lower or "add" in msg_lower or "car" in msg_lower or "bus" in msg_lower:
        return ("🚙 To add a vehicle, open the navigation sidebar menu (click the 3-line settings icon at the top-right), "
                "select **My Vehicles**, and click **+ Add Vehicle** on the top-right. Fill in the name, plate number, type, "
                "available seats, origin, destination, and fare details to activate it! 🚗")
    elif "booking" in msg_lower or "passenger" in msg_lower or "seat" in msg_lower:
        return ("📋 To view bookings, open the navigation sidebar and click **Bookings**. Here you can see passenger details, "
                "reserved seat maps (for route-based public vehicles), travel dates, contact numbers, and total fares. 💺")
    elif "revenue" in msg_lower or "money" in msg_lower or "earning" in msg_lower or "cost" in msg_lower or "fare" in msg_lower:
        return ("💰 Your total earnings and revenue are displayed on the main **Dashboard** stats cards, alongside the number of active "
                "vehicles, total bookings, and total seats booked. 📈")
    elif "setting" in msg_lower or "profile" in msg_lower or "edit" in msg_lower or "company" in msg_lower:
        return ("⚙️ To manage your profile or business details, open the navigation sidebar and click **Settings**. You can update your "
                "company name, contact person, alternate email, and notification preferences. 👤")
    elif any(word in msg_lower for word in ["help", "hi", "hello", "hey", "partner", "how to"]):
        return ("🚐 Welcome! I am your RoadBuddy Partner Assistant. I can guide you on how to list vehicles, manage bookings, check revenue, "
                "or update settings. How can I help you manage your fleet today? 😊")
    else:
        return "I can only answer questions related to our app."


async def call_groq_chat(messages: list[dict], system_prompt: str) -> str:
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    groq_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        groq_messages.append({"role": msg["role"], "content": msg["content"]})
    payload = {"model": GROQ_MODEL, "messages": groq_messages, "temperature": 0.5, "max_tokens": 800}
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(GROQ_URL, headers=headers, json=payload)
        if res.status_code != 200:
            print(f"Groq error: {res.status_code} — {res.text}")
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()


def find_best_vehicle_match(message: str, vehicles: list) -> tuple:
    msg_lower = message.lower()
    scored_vehicles = []

    for v in vehicles:
        name_lower = v.vehicle_name.lower()
        score = 0.0

        # 1. Exact match of the full name
        if name_lower in msg_lower:
            score = 100.0 + len(name_lower)
        else:
            # 2. Word token match
            name_words = [w for w in name_lower.split() if len(w) > 2]
            if name_words:
                matched_words = [w for w in name_words if w in msg_lower]
                if matched_words:
                    score = (len(matched_words) / len(name_words)) * 50.0
            else:
                # Fallback for short name vehicles
                if name_lower in msg_lower:
                    score = 25.0

        if score > 0.0:
            scored_vehicles.append((v, score))

    if not scored_vehicles:
        return None, 0.0

    scored_vehicles.sort(key=lambda x: x[1], reverse=True)

    # If top score is less than 100 (not exact full name match) and there are multiple matches
    if len(scored_vehicles) > 1 and scored_vehicles[0][1] < 100.0:
        best_v, best_s = scored_vehicles[0]
        second_v, second_s = scored_vehicles[1]
        if abs(best_s - second_s) < 5.0:
            return None, -1.0

    return scored_vehicles[0][0], scored_vehicles[0][1]


def format_to_24h(time_str: str) -> str:
    time_str = time_str.strip().upper()
    has_pm = "PM" in time_str
    has_am = "AM" in time_str

    clean_str = time_str.replace("AM", "").replace("PM", "").strip()
    parts = clean_str.split(":")
    if len(parts) == 2:
        try:
            h = int(parts[0])
            m = int(parts[1])
        except ValueError:
            return time_str
    elif len(parts) == 1:
        try:
            h = int(parts[0])
            m = 0
        except ValueError:
            return time_str
    else:
        return time_str

    if has_pm and h < 12:
        h += 12
    elif has_am and h == 12:
        h = 0

    return f"{h:02d}:{m:02d}"


def parse_vehicle_update(message: str, vehicles: list) -> dict:
    msg_lower = message.lower()

    # 1. Match vehicle
    matched_vehicle, best_score = find_best_vehicle_match(message, vehicles)

    if best_score == -1.0:
        return {"error": "Multiple vehicles matched your request. Please specify the exact vehicle name."}

    if not matched_vehicle:
        if len(vehicles) == 1:
            matched_vehicle = vehicles[0]
        else:
            return {"error": "Could not identify which vehicle listing you want to update. Please specify the vehicle name."}

    changes = {}
    descriptions = []

    # 2. Parse Fare
    is_fare = any(word in msg_lower for word in ["fare", "price", "rate", "cost", "rent", "seat fare"])
    if is_fare:
        import re
        nums = re.findall(r'\b\d+(?:\.\d+)?\b', message)
        if nums:
            val = float(nums[0])
            is_km = any(w in msg_lower for w in ["km", "kilometer", "distance"])
            if is_km:
                changes["price_per_km_inr"] = val
                descriptions.append(f"fare per KM to ₹{val}")
            else:
                changes["fixed_fare_inr"] = val
                if matched_vehicle.destination == "Rental" or not matched_vehicle.departure_time:
                    descriptions.append(f"daily rent to ₹{int(val)}")
                else:
                    descriptions.append(f"per-seat fare to ₹{int(val)}")

    # 3. Parse Timing
    is_timing = any(word in msg_lower for word in ["time", "timing", "departure", "arrival", "running"])
    if is_timing:
        import re
        time_pattern = r'\b(?:[01]?\d|2[0-3]):[0-5]\d\s*(?:am|pm|AM|PM)?\b|\b(?:[01]?\d)\s*(?:am|pm|AM|PM)\b'
        times = [t.strip() for t in re.findall(time_pattern, message, re.IGNORECASE)]

        if len(times) >= 2:
            dep_24 = format_to_24h(times[0])
            arr_24 = format_to_24h(times[1])
            changes["departure_time"] = dep_24
            changes["arrival_time"] = arr_24
            descriptions.append(f"timings to {dep_24} - {arr_24}")
        elif len(times) == 1:
            val_24 = format_to_24h(times[0])
            is_arrival = any(w in msg_lower for w in ["arrival", "arrive", "arrives", "ends", "reach"])
            if is_arrival:
                changes["arrival_time"] = val_24
                descriptions.append(f"arrival time to {val_24}")
            else:
                changes["departure_time"] = val_24
                descriptions.append(f"departure time to {val_24}")

    # 4. Parse Origin/Destination/Route
    is_route = any(w in msg_lower for w in ["origin", "destination", "route", "from", "to", "location", "city"])
    if is_route and not is_timing and not is_fare:
        import re
        from_city, to_city = None, None

        if "route" in msg_lower or ("from" in msg_lower and "to" in msg_lower and "origin" not in msg_lower and "destination" not in msg_lower):
            match_from_to = re.search(r'\bfrom\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)\b', message, re.IGNORECASE)
            if match_from_to:
                from_city = match_from_to.group(1).strip()
                to_city = match_from_to.group(2).strip()
                changes["origin"] = from_city
                changes["destination"] = to_city
                descriptions.append(f"route to {from_city} → {to_city}")
            else:
                match_simple_to = re.search(r'\b([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+?)$', message, re.IGNORECASE)
                if match_simple_to:
                    c1 = match_simple_to.group(1).strip()
                    c2 = match_simple_to.group(2).strip()
                    c1_words = c1.split()
                    if len(c1_words) <= 2:
                        changes["origin"] = c1
                        changes["destination"] = c2
                        descriptions.append(f"route to {c1} → {c2}")

        if "origin" not in changes and "destination" not in changes:
            city_match = re.search(r'\b(?:to|from|at|set|value|be)\s+([a-zA-Z\s]+?)$', message, re.IGNORECASE)
            if city_match:
                city = city_match.group(1).strip()
                is_origin = any(w in msg_lower for w in ["origin", "from", "source", "start"])
                is_dest = any(w in msg_lower for w in ["destination", "to", "end", "reach"])

                if "origin" in msg_lower:
                    changes["origin"] = city
                    descriptions.append(f"origin to {city}")
                elif "destination" in msg_lower:
                    changes["destination"] = city
                    descriptions.append(f"destination to {city}")
                elif is_origin and not is_dest:
                    changes["origin"] = city
                    descriptions.append(f"origin to {city}")
                elif is_dest and not is_origin:
                    changes["destination"] = city
                    descriptions.append(f"destination to {city}")

    # 5. Parse Stops/Pickups/Drop-offs
    is_pickup = any(w in msg_lower for w in ["pickup", "pickups", "pick-up"])
    is_dropoff = any(w in msg_lower for w in ["dropoff", "dropoffs", "drop-off"])
    if is_pickup or is_dropoff:
        import re
        match = re.search(r'\b(?:to|be|as)\s+([a-zA-Z0-9\s,;·\-\(\)]+)', message, re.IGNORECASE)
        if match:
            raw_stops = match.group(1).strip()
            stops_list = [s.strip() for s in re.split(r'[,;]|\band\b', raw_stops) if s.strip()]
            stops = ";".join(stops_list)
            if is_pickup:
                changes["pickup_points"] = stops
                descriptions.append(f"pickup points to {', '.join(stops_list)}")
            if is_dropoff:
                changes["dropoff_points"] = stops
                descriptions.append(f"drop-off points to {', '.join(stops_list)}")

    # 6. Parse Dates
    is_date = any(w in msg_lower for w in ["date", "dates"])
    if is_date:
        import re
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', message)
        if dates:
            changes["service_dates"] = ",".join(dates)
            descriptions.append(f"service dates to {', '.join(dates)}")

    if not changes:
        return {"error": "I couldn't identify what details you want to update (timings, fare, stops, dates, etc.). Please specify."}

    return {
        "vehicle_id": matched_vehicle.id,
        "vehicle_name": matched_vehicle.vehicle_name,
        "changes": changes,
        "description": " and ".join(descriptions)
    }


def try_intercept_vehicle_update_flow(message: str, history: list[dict], provider_id: int, db: Session) -> str:
    msg_lower = message.lower()

    # Do not intercept show/list/display/my vehicles queries — these are data requests, not updates
    is_show_or_list = any(phrase in msg_lower for phrase in [
        "show my vehicle", "list my vehicle", "my vehicles", "show vehicle",
        "list vehicle", "display my vehicle", "display vehicle", "what are my vehicle"
    ])
    if is_show_or_list:
        return None

    # Check if the last assistant message in history asked the question
    asked_question = False
    original_update_message = None

    if history:
        assistant_msgs = [h for h in history if h.get("role") == "assistant"]
        if assistant_msgs:
            last_assist = assistant_msgs[-1]["content"].strip()
            if "do you want me to do it for you or do you want to do it manually" in last_assist.lower():
                asked_question = True
                for i in range(len(history) - 1, -1, -1):
                    if history[i].get("role") == "assistant" and "do you want me to do it for you or do you want to do it manually" in history[i].get("content", "").lower():
                        for j in range(i - 1, -1, -1):
                            if history[j].get("role") == "user":
                                original_update_message = history[j]["content"]
                                break
                        break

    from app.models.models import ProviderVehicle
    vehicles = db.query(ProviderVehicle).filter(ProviderVehicle.provider_id == provider_id).all()
    if not vehicles:
        return None

    if asked_question and original_update_message:
        is_auto = any(w in msg_lower for w in ["do it for me", "yes", "please", "for me", "do it", "auto", "automatically", "sure", "ok", "okay"])
        is_manual = any(w in msg_lower for w in ["manual", "manually", "i will do it", "myself"])

        if is_auto:
            parse_result = parse_vehicle_update(original_update_message, vehicles)
            if "error" in parse_result:
                return f"Sorry, I couldn't process the update details from your original request: {parse_result['error']}"

            vehicle = db.query(ProviderVehicle).filter(ProviderVehicle.id == parse_result["vehicle_id"]).first()
            if not vehicle:
                return "Error: Vehicle listing not found."

            for k, v in parse_result["changes"].items():
                setattr(vehicle, k, v)
            db.commit()
            db.refresh(vehicle)

            return f"✅ Done! I have updated the {parse_result['description']} of **{parse_result['vehicle_name']}**."

        elif is_manual:
            return ("🚙 To edit manually, click the edit button (✏️) next to the vehicle listing on the **My Vehicles** page. "
                    "It will open a modal where you can edit the origin, destination, timings, stops, and service dates.")
        else:
            pass

    # Avoid matching guidance questions
    is_asking_guidance = any(word in msg_lower for word in [
        "how", "guide", "steps", "where do", "instruct", "tutorial", "process",
        "show", "list", "display", "what are"
    ])
    if is_asking_guidance:
        return None

    # Check for update verbs/intents
    update_verbs = ["update", "change", "set", "add", "edit", "delete", "modify", "put", "make", "increase", "decrease", "adjust", "reduce", "remove", "reset", "clear", "fix", "should be", "to be"]
    has_update_verb = any(word in msg_lower for word in update_verbs)

    question_starters = ["what", "why", "who", "where", "when", "is ", "are ", "does ", "do ", "did ", "was ", "were ", "has ", "have ", "had ", "show "]
    is_question = any(msg_lower.startswith(q) for q in question_starters)

    if is_question and not has_update_verb:
        return None

    parse_result = parse_vehicle_update(message, vehicles)
    if "error" in parse_result:
        if has_update_verb:
            return parse_result["error"]
        return None

    if is_question and not has_update_verb:
        return None

    return "Do you want me to do it for you or do you want to do it manually?"


async def chat_with_provider_bot(message: str, history: list[dict] = None, provider_id: int = None, db: Session = None) -> dict:
    try:
        raw_history = history or []
        filtered_history = [h for h in raw_history if h.get("role") in ("user", "assistant")]
        truncated_history = filtered_history[-10:]

        messages = truncated_history + [{"role": "user", "content": message}]

        # Guard rails check for out-of-scope keywords before anything else
        msg_lower = message.lower()
        non_app_words = ["weather", "code", "python", "javascript", "history", "recipe", "cook", "capital", "president", "prime minister", "who is", "who was", "write a"]
        app_words = ["vehicle", "booking", "revenue", "setting", "earning", "partner", "roadbuddy", "profile", "logout", "login", "register"]

        is_out_of_scope = any(word in msg_lower for word in non_app_words) and not any(word in msg_lower for word in app_words)

        if is_out_of_scope:
            response_text = "I can only answer questions related to our app."
            updated_history = messages + [{"role": "assistant", "content": response_text}]
            return {"response": response_text, "history": updated_history, "total_messages": len(updated_history)}

        # Check for vehicle update commands
        if db and provider_id:
            update_response = try_intercept_vehicle_update_flow(message, raw_history, provider_id, db)
            if update_response:
                updated_history = messages + [{"role": "assistant", "content": update_response}]
                return {"response": update_response, "history": updated_history, "total_messages": len(updated_history)}

        if settings.groq_api_key:
            try:
                dynamic_prompt = SYSTEM_PROMPT
                if db and provider_id:
                    summary = get_provider_data_summary(provider_id, db)
                    dynamic_prompt += f"\n\n{summary}"
                response_text = await call_groq_chat(messages, dynamic_prompt)
            except Exception as e:
                print(f"Groq provider chat failed: {e}. Falling back to mock response.")
                response_text = mock_partner_chat_response(message, provider_id, db)
        else:
            response_text = mock_partner_chat_response(message, provider_id, db)

        response_text = response_text.strip().strip('"').strip("'").strip()
        if "I can only answer questions related to our app" in response_text:
            response_text = "I can only answer questions related to our app."
        updated_history = messages + [{"role": "assistant", "content": response_text}]
        return {"response": response_text, "history": updated_history, "total_messages": len(updated_history)}

    except Exception as e:
        raise RuntimeError(f"Partner chat failed: {e}") from e