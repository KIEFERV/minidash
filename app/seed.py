"""Demo data. Loaded only when the restaurants table is empty."""
import sqlite3

# (name, cuisine, opens_at, closes_at, avg_prep_minutes, [(item, price_cents), ...])
SEED_DATA = [
    (
        "Napoli Slice", "Italian", "11:00", "23:00", 20,
        [
            ("Margherita Pizza", 1200),
            ("Pepperoni Pizza", 1400),
            ("Spaghetti Carbonara", 1350),
            ("Garlic Knots", 600),
            ("Tiramisu", 700),
        ],
    ),
    (
        "Golden Wok", "Chinese", "11:30", "22:00", 25,
        [
            ("Kung Pao Chicken", 1450),
            ("Vegetable Lo Mein", 1200),
            ("Pork Dumplings (8)", 900),
            ("Hot & Sour Soup", 500),
            ("Egg Fried Rice", 800),
        ],
    ),
    (
        # Overnight hours: open 10:00 until 02:00 the next morning.
        "Taco Libre", "Mexican", "10:00", "02:00", 15,
        [
            ("Carne Asada Taco", 450),
            ("Al Pastor Taco", 425),
            ("Chicken Burrito", 1100),
            ("Chips & Guacamole", 650),
            ("Horchata", 350),
        ],
    ),
    (
        "Green Bowl", "Healthy", "08:00", "20:00", 10,
        [
            ("Harvest Grain Bowl", 1300),
            ("Caesar Salad", 1100),
            ("Avocado Toast", 950),
            ("Green Smoothie", 700),
            ("Falafel Wrap", 1050),
        ],
    ),
    (
        # opens_at == closes_at means open 24 hours.
        "Midnight Diner", "American", "00:00", "00:00", 18,
        [
            ("Classic Cheeseburger", 1250),
            ("Buttermilk Pancakes", 1000),
            ("Club Sandwich", 1150),
            ("Loaded Fries", 800),
            ("Chocolate Milkshake", 650),
        ],
    ),
]


def seed(conn: sqlite3.Connection) -> None:
    with conn:
        for name, cuisine, opens_at, closes_at, prep, menu in SEED_DATA:
            cur = conn.execute(
                "INSERT INTO restaurants (name, cuisine, opens_at, closes_at, avg_prep_minutes) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, cuisine, opens_at, closes_at, prep),
            )
            conn.executemany(
                "INSERT INTO menu_items (restaurant_id, name, price_cents) VALUES (?, ?, ?)",
                [(cur.lastrowid, item, price) for item, price in menu],
            )
