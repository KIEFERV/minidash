"""SQL for restaurants and menu items. Returns plain dicts."""
import sqlite3


class RestaurantRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_all(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM restaurants ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def get(self, restaurant_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM restaurants WHERE id = ?", (restaurant_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_menu(self, restaurant_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM menu_items WHERE restaurant_id = ? ORDER BY id",
            (restaurant_id,),
        ).fetchall()
        return [dict(r) for r in rows]
