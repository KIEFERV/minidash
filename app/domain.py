"""Pure business rules: no web framework, no database."""
from datetime import datetime, time, timedelta
from enum import Enum


class OrderStatus(str, Enum):
    SCHEDULED = "scheduled"          # held until shortly before delivery time
    PLACED = "placed"                # with the restaurant (immediate or released)
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Transitions a client may request through PATCH /orders/{id}/status.
# SCHEDULED -> PLACED is deliberately absent: it is done only by the system,
# exactly once, at release time (see OrderService.release_due_orders).
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.SCHEDULED: {OrderStatus.CANCELLED},
    OrderStatus.PLACED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def can_transition(current: OrderStatus, new: OrderStatus) -> bool:
    return new in ALLOWED_TRANSITIONS[current]


# ---------------------------------------------------------------- opening hours
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


# ---------------------------------------------------------------- scheduling
MIN_SCHEDULE_LEAD = timedelta(minutes=45)
MAX_SCHEDULE_LEAD = timedelta(days=7)
RELEASE_LEAD = timedelta(minutes=30)  # released this long before delivery time


def parse_scheduled_time(raw: str) -> datetime | None:
    """Parse a client-supplied delivery time into naive server-local time.

    Accepts ISO 8601 ("2026-11-02T18:30:00"). A trailing "Z" or a UTC offset
    is converted to server-local time. Returns None if the text is not a
    full date-and-time. Sub-second precision is dropped.
    """
    value = raw.strip()
    if "T" not in value and " " not in value:  # reject date-only strings
        return None
    if value[-1:] in ("Z", "z"):
        value = value[:-1] + "+00:00"  # fromisoformat() only learned "Z" in 3.11
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
    except (ValueError, OverflowError, OSError):
        return None
    return parsed.replace(microsecond=0)


def is_valid_schedule_time(scheduled_for: datetime, now: datetime) -> bool:
    """At least 45 minutes and at most 7 days ahead (both bounds inclusive)."""
    return MIN_SCHEDULE_LEAD <= scheduled_for - now <= MAX_SCHEDULE_LEAD


def release_time(scheduled_for: datetime) -> datetime:
    """When a scheduled order is handed to the restaurant."""
    return scheduled_for - RELEASE_LEAD
