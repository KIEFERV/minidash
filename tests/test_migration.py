"""A database created by the first version of MiniDash keeps working."""
import sqlite3

from app.database import connect, init_db

OLD_SCHEMA = """
CREATE TABLE restaurants (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
    cuisine TEXT NOT NULL, opens_at TEXT NOT NULL, closes_at TEXT NOT NULL,
    avg_prep_minutes INTEGER NOT NULL);
CREATE TABLE menu_items (id INTEGER PRIMARY KEY AUTOINCREMENT, restaurant_id INTEGER NOT NULL,
    name TEXT NOT NULL, price_cents INTEGER NOT NULL);
CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, restaurant_id INTEGER NOT NULL,
    status TEXT NOT NULL, total_cents INTEGER NOT NULL, address TEXT NOT NULL,
    created_at TEXT NOT NULL);
CREATE TABLE order_items (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
    menu_item_id INTEGER NOT NULL, quantity INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL);
INSERT INTO restaurants (name, cuisine, opens_at, closes_at, avg_prep_minutes)
    VALUES ('Old Place', 'Test', '00:00', '00:00', 10);
INSERT INTO orders (restaurant_id, status, total_cents, address, created_at)
    VALUES (1, 'pending', 500, 'Old Street', '2026-01-01T12:00:00'),
           (1, 'delivered', 700, 'Old Street', '2026-01-01T13:00:00');
"""


def test_old_database_gains_new_columns_and_status_name(tmp_path):
    path = str(tmp_path / "old.db")
    raw = sqlite3.connect(path)
    raw.executescript(OLD_SCHEMA)
    raw.close()

    init_db(path)
    init_db(path)  # running the migration twice is harmless

    conn = connect(path)
    columns = {r["name"] for r in conn.execute("PRAGMA table_info(orders)")}
    assert {"scheduled_for", "release_at", "released_at"} <= columns
    statuses = [r["status"] for r in conn.execute("SELECT status FROM orders ORDER BY id")]
    assert statuses == ["placed", "delivered"]
    assert conn.execute("SELECT COUNT(*) FROM restaurants").fetchone()[0] == 1  # not re-seeded
    conn.close()
