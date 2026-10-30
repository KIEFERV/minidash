"""SQL for orders and order items. Returns plain dicts."""
import sqlite3


class OrderRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(
        self,
        restaurant_id: int,
        status: str,
        total_cents: int,
        address: str,
        created_at: str,
        lines: list[tuple[int, int, int]],
    ) -> int:
        """Insert an order and its lines atomically.

        ``lines`` holds (menu_item_id, quantity, unit_price_cents) tuples.
        Returns the new order id.
        """
        with self.conn:  # one transaction: commit on success, roll back on error
            cur = self.conn.execute(
                "INSERT INTO orders (restaurant_id, status, total_cents, address, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (restaurant_id, status, total_cents, address, created_at),
            )
            order_id = cur.lastrowid
            self.conn.executemany(
                "INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price_cents) "
                "VALUES (?, ?, ?, ?)",
                [(order_id, *line) for line in lines],
            )
        return order_id

    def get(self, order_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_items(self, order_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT oi.menu_item_id, mi.name, oi.quantity, oi.unit_price_cents "
            "FROM order_items oi JOIN menu_items mi ON mi.id = oi.menu_item_id "
            "WHERE oi.order_id = ? ORDER BY oi.id",
            (order_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_status(self, order_id: int, status: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE orders SET status = ? WHERE id = ?", (status, order_id)
            )
