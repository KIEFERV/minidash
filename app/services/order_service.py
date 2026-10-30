from datetime import datetime

from app.domain import OrderStatus, can_transition, is_open
from app.errors import ConflictError, NotFoundError, UnprocessableError
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository


class OrderService:
    def __init__(
        self,
        orders: OrderRepository,
        restaurants: RestaurantRepository,
        now: datetime,
    ):
        self.orders = orders
        self.restaurants = restaurants
        self.now = now  # injected so tests can control the clock

    def create_order(
        self,
        restaurant_id: int,
        address: str,
        items: list[tuple[int, int]],
    ) -> dict:
        """Create a pending order. ``items`` is a list of (menu_item_id, quantity)."""
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

        if not is_open(restaurant["opens_at"], restaurant["closes_at"], self.now):
            raise ConflictError(
                f"{restaurant['name']} is closed right now "
                f"(open {restaurant['opens_at']}-{restaurant['closes_at']})"
            )

        # Prices come from the menu, never from the client.
        lines = [
            (menu_item_id, quantity, menu[menu_item_id]["price_cents"])
            for menu_item_id, quantity in quantities.items()
        ]
        total_cents = sum(quantity * price for _, quantity, price in lines)

        order_id = self.orders.create(
            restaurant_id=restaurant_id,
            status=OrderStatus.PENDING.value,
            total_cents=total_cents,
            address=address,
            created_at=self.now.isoformat(timespec="seconds"),
            lines=lines,
        )
        return self.get_order(order_id)

    def get_order(self, order_id: int) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")
        order["items"] = self.orders.list_items(order_id)
        return order

    def update_status(self, order_id: int, new_status: OrderStatus) -> dict:
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")

        current = OrderStatus(order["status"])
        if not can_transition(current, new_status):
            raise ConflictError(
                f"Cannot change order status from '{current.value}' to '{new_status.value}'"
            )
        self.orders.update_status(order_id, new_status.value)
        return self.get_order(order_id)
