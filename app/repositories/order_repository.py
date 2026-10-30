"""SQL for orders and order items. Returns plain dicts."""
import sqlite3

from app.domain import OrderStatus


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
        scheduled_for: str | None = None,
        release_at: str | None = None,
    ) -> int:
        """Insert an order and its lines atomically.

        ``lines`` holds (menu_item_id, quantity, unit_price_cents) tuples.
        Returns the new order id.
        """
        with self.conn:  # one transaction: commit on success, roll back on error
            cur = self.conn.execute(
                "INSERT INTO orders (restaurant_id, status, total_cents, address, created_at, "
                "scheduled_for, release_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (restaurant_id, status, total_cents, address, created_at,
                 scheduled_for, release_at),
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

    def update_status(self, order_id: int, expected: str, new: str) -> bool:
        """Compare-and-set: change the status only if it is still ``expected``.

        Returns False if another request changed the order in the meantime.
        """
        with self.conn:
            cur = self.conn.execute(
                "UPDATE orders SET status = ? WHERE id = ? AND status = ?",
                (new, order_id, expected),
            )
        return cur.rowcount == 1

    def release_due(self, now: str, order_id: int | None = None) -> list[int]:
        """Move due SCHEDULED orders to PLACED and return the ids moved.

        An order is due when its ``release_at`` is not after ``now``. Each
        UPDATE only matches rows that are still SCHEDULED, so an order is
        released at most once even if several callers (the background job and
        request handlers) race, and a cancelled order is never resurrected.
        Pass ``order_id`` to consider a single order.
        """
        sql = "SELECT id FROM orders WHERE status = ? AND release_at <= ?"
        params: list = [OrderStatus.SCHEDULED.value, now]
        if order_id is not None:
            sql += " AND id = ?"
            params.append(order_id)
        due = [r["id"] for r in self.conn.execute(sql + " ORDER BY release_at, id", params)]

        released = []
        with self.conn:
            for oid in due:
                cur = self.conn.execute(
                    "UPDATE orders SET status = ?, released_at = ? WHERE id = ? AND status = ?",
                    (OrderStatus.PLACED.value, now, oid, OrderStatus.SCHEDULED.value),
                )
                if cur.rowcount == 1:
                    released.append(oid)
        return released
