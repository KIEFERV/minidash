from datetime import datetime

from app.domain import (
    OrderStatus,
    can_transition,
    is_open,
    is_valid_schedule_time,
    parse_scheduled_time,
    release_time,
)
from app.errors import ConflictError, NotFoundError, UnprocessableError
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository

INVALID_TIME_MESSAGE = "Please enter a valid time"


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        restaurants: RestaurantRepository,
        now: datetime,
    ):
        self.orders = orders
        self.restaurants = restaurants
        self.now = now  # taken from the injected clock; never call datetime.now() here

    def _now_str(self) -> str:
        return self.now.isoformat(timespec="seconds")

    def create_order(
        self,
        restaurant_id: int,
        address: str,
        items: list[tuple[int, int]],
        scheduled_for: str | None = None,
    ) -> dict:
        """Create an order. ``items`` is a list of (menu_item_id, quantity).

        Without ``scheduled_for`` the order is placed immediately and the
        restaurant must be open now. With it, the order is held as SCHEDULED
        and the restaurant must be open at the delivery time.
        """
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None:
            raise NotFoundError(f"Restaurant {restaurant_id} not found")

        # Merge repeated menu items into a single line.
        quantities: dict[int, int] = {}
        for menu_item_id, quantity in items:
            quantities[menu_item_id] = quantities.get(menu_item_id, 0) + quantity

        menu = {m["id"]: m for m in self.restaurants.list_menu(restaurant_id)}
        unknown = sorted(set(quantities) - set(menu))
        if unknown:
            raise UnprocessableError(
                f"Menu items {unknown} do not belong to restaurant {restaurant_id}"
            )

        hours = f"open {restaurant['opens_at']}-{restaurant['closes_at']}"
        scheduled_at = None
        if scheduled_for is not None:
            scheduled_at = parse_scheduled_time(scheduled_for)
            if scheduled_at is None or not is_valid_schedule_time(scheduled_at, self.now):
                raise UnprocessableError(INVALID_TIME_MESSAGE)
            if not is_open(restaurant["opens_at"], restaurant["closes_at"], scheduled_at):
                raise ConflictError(
                    f"{restaurant['name']} is closed at the requested delivery time ({hours})"
                )
        elif not is_open(restaurant["opens_at"], restaurant["closes_at"], self.now):
            raise ConflictError(f"{restaurant['name']} is closed right now ({hours})")

        # Prices come from the menu, never from the client.
        lines = [
            (menu_item_id, quantity, menu[menu_item_id]["price_cents"])
            for menu_item_id, quantity in quantities.items()
        ]
        total_cents = sum(quantity * price for _, quantity, price in lines)

        order_id = self.orders.create(
            restaurant_id=restaurant_id,
            status=(OrderStatus.SCHEDULED if scheduled_at else OrderStatus.PLACED).value,
            total_cents=total_cents,
            address=address,
            created_at=self._now_str(),
            lines=lines,
            scheduled_for=scheduled_at.isoformat(timespec="seconds") if scheduled_at else None,
            release_at=release_time(scheduled_at).isoformat(timespec="seconds")
            if scheduled_at
            else None,
        )
        return self.get_order(order_id)

    def get_order(self, order_id: int) -> dict:
        # Release this order first if its time has come, so the answer is right
        # even if the background job has not run yet.
        self.orders.release_due(self._now_str(), order_id)
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")
        order["items"] = self.orders.list_items(order_id)
        return order

    def update_status(self, order_id: int, new_status: OrderStatus) -> dict:
        self.orders.release_due(self._now_str(), order_id)  # see get_order
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")

        current = OrderStatus(order["status"])
        if current is OrderStatus.SCHEDULED and new_status is OrderStatus.PLACED:
            raise ConflictError(
                "A scheduled order is released automatically 30 minutes before its delivery time"
            )
        if not can_transition(current, new_status):
            raise ConflictError(
                f"Cannot change order status from '{current.value}' to '{new_status.value}'"
            )
        if not self.orders.update_status(order_id, current.value, new_status.value):
            raise ConflictError("The order was changed by another request; please try again")
        return self.get_order(order_id)

    def release_due_orders(self) -> list[int]:
        """Release every scheduled order whose release time has arrived.

        Idempotent: each order moves SCHEDULED -> PLACED exactly once. Returns
        the ids released by this call.
        """
        return self.orders.release_due(self._now_str())
