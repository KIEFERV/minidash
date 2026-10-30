"""Pure business rules: no web framework, no database."""
from datetime import datetime, time
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# An order moves forward one step at a time and can be cancelled until the
# kitchen has started cooking. DELIVERED and CANCELLED are terminal.
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def can_transition(current: OrderStatus, new: OrderStatus) -> bool:
    return new in ALLOWED_TRANSITIONS[current]


def is_open(opens_at: str, closes_at: str, now: datetime) -> bool:
    """Is a restaurant open at ``now``? Hours are "HH:MM" strings.

    * opens_at < closes_at   -> same-day window, e.g. 11:00-23:00
    * opens_at > closes_at   -> overnight window, e.g. 10:00-02:00
    * opens_at == closes_at  -> open 24 hours
    The opening time is inclusive, the closing time exclusive.
    """
    opens = time.fromisoformat(opens_at)
    closes = time.fromisoformat(closes_at)
    current = now.time()
    if opens == closes:
        return True
    if opens < closes:
        return opens <= current < closes
    return current >= opens or current < closes
