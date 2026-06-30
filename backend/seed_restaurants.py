import os
import sys
import random

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.models.models import Base, Restaurant, MenuItem, FoodReview, User

CITIES = [
    "Delhi", "Jaipur", "Udaipur", "Agra", "Ajmer", 
    "Mumbai", "Goa", "Pune", "Ahmedabad", "Bengaluru"
]

RESTAURANT_NAMES_PREFIX = [
    "Sher-E-Punjab", "Highway Dhaba", "The Royal Kitchen", "Spice Junction", "Darbar",
    "Giani's", "Bikanervala", "Haldiram's", "Apni Rasoi", "Shree Rathnam", "Sagar Ratna",
    "Chokhi Dhani Café", "Grand Mewar", "Lakeside Grill", "The Taj View Café", "Taj Mahal Dhaba",
    "Goan Fish House", "Britto's Highway", "South Feast", "Udupi Garden", "MTR Express",
    "The Parsi Cafe", "Mumbai Masala", "Konkan Kinara", "Gujarati Thali House", "Kathiawadi Dhaba"
]

RESTAURANT_SUFFIXES = [
    "Dhaba", "Restaurant", "Café", "Bistro", "Family Restaurant", "Lounge", "Junction", "Eatery", "Point"
]

DISHES_BY_CATEGORY = {
    "Veg": [
        ("Paneer Butter Masala", "Rich and creamy cottage cheese gravy.", 260.0),
        ("Dal Makhani", "Slow-cooked black lentils with cream and butter.", 220.0),
        ("Aloo Gobi", "Classic dry cauliflower and potato dish.", 160.0),
        ("Chana Masala", "Spicy chickpeas cooked in tomato-onion gravy.", 180.0),
        ("Kadhai Paneer", "Cottage cheese cooked with bell peppers and spices.", 270.0),
        ("Veg Biryani", "Fragrant basmati rice cooked with mixed vegetables.", 240.0),
        ("Masala Dosa", "Crispy rice crepe with potato filling.", 140.0),
        ("Butter Naan", "Soft leavened flatbread with butter.", 50.0),
        ("Tandoori Roti", "Whole wheat bread baked in clay oven.", 25.0),
        ("Malai Kofta", "Fried potato and paneer balls in sweet creamy gravy.", 280.0)
    ],
    "Non-Veg": [
        ("Butter Chicken", "Tender chicken in a rich, buttery tomato gravy.", 340.0),
        ("Chicken Tikka Masala", "Grilled chicken chunks in a spicy spiced sauce.", 320.0),
        ("Mutton Rogan Josh", "Slow-cooked lamb in Kashmiri spices.", 420.0),
        ("Chicken Biryani", "Basmati rice layered with spiced chicken.", 290.0),
        ("Goan Fish Curry", "Traditional fish curry cooked in coconut milk.", 360.0),
        ("Egg Curry", "Boiled eggs cooked in spicy onion tomato gravy.", 190.0),
        ("Kadhai Chicken", "Chicken cooked in a thick bell pepper sauce.", 310.0)
    ],
    "Beverage": [
        ("Masala Chai", "Spiced Indian tea brewed with milk.", 40.0),
        ("Lassi", "Sweet, thick yogurt-based drink with cardamom.", 80.0),
        ("Filter Coffee", "Traditional South Indian chicory blend coffee.", 50.0),
        ("Fresh Lime Soda", "Refreshing sweet and salty lemon carbonated drink.", 70.0),
        ("Mango Shake", "Thick mango flavored milk shake.", 90.0)
    ],
    "Dessert": [
        ("Gulab Jamun", "Soft fried dough balls soaked in sugar syrup.", 60.0),
        ("Kheer", "Creamy rice pudding topped with dry fruits.", 80.0),
        ("Kulfi", "Traditional Indian dense frozen dairy dessert.", 90.0),
        ("Rasmalai", "Soft cottage cheese patties in sweetened saffron milk.", 110.0)
    ]
}

REVIEWS_COMMENTS = [
    "Amazing food! The butter paneer was absolutely delicious.",
    "Very clean dhaba along the highway. Highly recommended for families.",
    "Nice food but the service was a bit slow.",
    "Decent prices and great hygiene. 10/10.",
    "Filter coffee was refreshing, thali was huge and tasty!",
    "Amazing Butter Chicken, soft naan! Will visit again.",
    "A bit overpriced but the food quality is excellent."
]

def generate_restaurants():
    restaurants = []
    # Seed 100+ restaurants
    # 10 restaurants per city across 10 cities = 100 restaurants total
    restaurant_id_counter = 1
    
    for city in CITIES:
        for idx in range(1, 12):  # 11 per city = 110 total
            name = f"{random.choice(RESTAURANT_NAMES_PREFIX)} {random.choice(RESTAURANT_SUFFIXES)}"
            # Avoid direct duplicate names in same city
            name = f"{name} ({idx})"
            address = f"Highway NH-48, Milestone {random.randint(10, 280)}, near {city}"
            rating = round(random.uniform(3.8, 4.9), 1)
            rev_count = random.randint(15, 250)
            
            # Approximate lat-lons based on city
            lat_offsets = {
                "Delhi": (28.61, 77.20), "Jaipur": (26.91, 75.78), "Udaipur": (24.58, 73.71),
                "Agra": (27.17, 78.00), "Ajmer": (26.44, 74.63), "Mumbai": (19.07, 72.87),
                "Goa": (15.29, 74.12), "Pune": (18.52, 73.85), "Ahmedabad": (23.02, 72.57),
                "Bengaluru": (12.97, 77.59)
            }
            base_lat, base_lon = lat_offsets.get(city, (25.0, 75.0))
            lat = base_lat + random.uniform(-0.15, 0.15)
            lon = base_lon + random.uniform(-0.15, 0.15)
            
            rest = Restaurant(
                id=restaurant_id_counter,
                name=name,
                city=city,
                address=address,
                rating=rating,
                reviews_count=rev_count,
                latitude=lat,
                longitude=lon,
                contact_number=f"+91 {random.randint(7000000000, 9999999999)}"
            )
            restaurants.append(rest)
            restaurant_id_counter += 1
            
    return restaurants

def seed():
    print("Checking database for restaurants...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        has_rest = db.query(Restaurant).first() is not None
        if has_rest:
            print("Restaurants are already seeded. Skipping.")
            return

        # Ensure we have at least one user to write reviews
        user = db.query(User).first()
        if not user:
            user = User(name="Kundi", email="kundi@gmail.com", password_hash="dummy")
            db.add(user)
            db.commit()
            db.refresh(user)

        print("Generating 100+ restaurants...")
        restaurants = generate_restaurants()
        db.add_all(restaurants)
        db.commit()
        print(f"Added {len(restaurants)} restaurants.")

        print("Generating menu items and reviews...")
        menu_item_counter = 1
        menu_items_to_add = []
        reviews_to_add = []

        for r in restaurants:
            # Seed 6-9 menu items per restaurant
            seeded_categories = ["Veg", "Non-Veg", "Beverage", "Dessert"]
            for cat in seeded_categories:
                # Pick 1-3 items from this category
                available_dishes = DISHES_BY_CATEGORY[cat]
                chosen_dishes = random.sample(available_dishes, random.randint(1, 2))
                
                for dish_name, desc, base_price in chosen_dishes:
                    item_rating = round(random.uniform(3.8, 4.9), 1)
                    # Add slight pricing variation depending on restaurant
                    price = round(base_price + random.uniform(-20.0, 40.0), 0)
                    price = max(price, 15.0)  # Keep price positive
                    
                    item = MenuItem(
                        id=menu_item_counter,
                        restaurant_id=r.id,
                        name=dish_name,
                        description=desc,
                        price_inr=price,
                        category=cat,
                        rating=item_rating
                    )
                    menu_items_to_add.append(item)
                    
                    # Generate 1-2 reviews for this item
                    for _ in range(random.randint(1, 2)):
                        review = FoodReview(
                            user_id=user.id,
                            menu_item_id=menu_item_counter,
                            rating=random.randint(4, 5),
                            comment=random.choice(REVIEWS_COMMENTS)
                        )
                        reviews_to_add.append(review)
                        
                    menu_item_counter += 1

        db.add_all(menu_items_to_add)
        db.commit()
        db.add_all(reviews_to_add)
        db.commit()
        
        print(f"[SUCCESS] Seeded {len(restaurants)} restaurants, {len(menu_items_to_add)} menu items, and {len(reviews_to_add)} reviews successfully!")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
