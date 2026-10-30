"""SQLite connection helper, schema and first-run seeding."""
import sqlite3

from app.seed import seed

SCHEMA = """
CREATE TABLE IF NOT EXISTS restaurants (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    cuisine          TEXT    NOT NULL,
    opens_at         TEXT    NOT NULL,  -- "HH:MM"
    closes_at        TEXT    NOT NULL,  -- "HH:MM"
    avg_prep_minutes INTEGER NOT NULL CHECK (avg_prep_minutes > 0)
);

CREATE TABLE IF NOT EXISTS menu_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    name          TEXT    NOT NULL,
    price_cents   INTEGER NOT NULL CHECK (price_cents >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id),
    status        TEXT    NOT NULL,
    total_cents   INTEGER NOT NULL CHECK (total_cents >= 0),
    address       TEXT    NOT NULL,
    created_at    TEXT    NOT NULL      -- ISO 8601, server local time
);

-- unit_price_cents is a snapshot of the menu price at order time, so later
-- menu changes never alter past orders.
CREATE TABLE IF NOT EXISTS order_items (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id         INTEGER NOT NULL REFERENCES orders(id),
    menu_item_id     INTEGER NOT NULL REFERENCES menu_items(id),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0)
);

CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant ON menu_items(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order     ON order_items(order_id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may run a request's dependency and its
    # endpoint on different worker threads. Each request has its own connection,
    # so it is never used by two threads at once.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    """Create tables if missing and seed demo data into an empty database."""
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0] == 0:
            seed(conn)
    finally:
        conn.close()
