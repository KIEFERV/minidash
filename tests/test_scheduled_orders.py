from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import NOON

INVALID_TIME = "Please enter a valid time"
ADDRESS = "12 Main Street"
DELIVERY = NOON + timedelta(hours=2)        # 14:00
RELEASE = DELIVERY - timedelta(minutes=30)  # 13:30


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def menu_of(client, restaurant) -> list[dict]:
    return client.get(f"/restaurants/{restaurant['id']}/menu").json()


def schedule(client, restaurant, scheduled_for):
    item = menu_of(client, restaurant)[0]
    return client.post("/orders", json={
        "restaurant_id": restaurant["id"],
        "address": ADDRESS,
        "items": [{"menu_item_id": item["id"], "quantity": 1}],
        "scheduled_for": scheduled_for,
    })


def set_status(client, order_id, status):
    return client.patch(f"/orders/{order_id}/status", json={"status": status})


def fetch(client, order_id) -> dict:
    return client.get(f"/orders/{order_id}").json()


@pytest.fixture
def napoli(restaurants):
    return restaurants["Napoli Slice"]  # open 11:00-23:00


@pytest.fixture
def scheduled_order(client, napoli):
    """A SCHEDULED order for 14:00 (released at 13:30), created at noon."""
    response = schedule(client, napoli, iso(DELIVERY))
    assert response.status_code == 201
    return response.json()


# ---------------------------------------------------------------- creating
def test_scheduled_order_is_held_as_scheduled(client, napoli, scheduled_order):
    item = menu_of(client, napoli)[0]

    assert scheduled_order["status"] == "scheduled"
    assert scheduled_order["scheduled_for"] == iso(DELIVERY)
    assert scheduled_order["released_at"] is None
    assert scheduled_order["total_cents"] == item["price_cents"]
    assert scheduled_order["created_at"] == iso(NOON)


@pytest.mark.parametrize("body_value", ["omitted", "null"])
def test_order_without_a_schedule_is_placed_immediately(client, napoli, body_value):
    item = menu_of(client, napoli)[0]
    payload = {"restaurant_id": napoli["id"], "address": ADDRESS,
               "items": [{"menu_item_id": item["id"], "quantity": 1}]}
    if body_value == "null":
        payload["scheduled_for"] = None

    body = client.post("/orders", json=payload).json()

    assert body["status"] == "placed"
    assert body["scheduled_for"] is None
    assert body["released_at"] is None


# ---------------------------------------------------------------- the 45 min .. 7 day window
@pytest.mark.parametrize(
    "offset, accepted",
    [
        (timedelta(minutes=45), True),
        (timedelta(minutes=44, seconds=59), False),
        (timedelta(minutes=10), False),
        (timedelta(0), False),
        (timedelta(minutes=-30), False),            # in the past
        (timedelta(days=7), True),
        (timedelta(days=7, seconds=1), False),
    ],
    ids=["exactly-45min", "just-under-45min", "10min", "now", "past", "exactly-7days",
         "just-over-7days"],
)
def test_delivery_time_must_be_45_minutes_to_7_days_ahead(client, napoli, offset, accepted):
    response = schedule(client, napoli, iso(NOON + offset))

    if accepted:
        assert response.status_code == 201
    else:
        assert response.status_code == 422
        assert response.json()["detail"] == INVALID_TIME


@pytest.mark.parametrize(
    "text",
    ["tomorrow", "", "   ", "2026-10-29", "29/10/2026 18:00", "2026-13-45T10:00:00"],
)
def test_unparseable_delivery_time_returns_the_same_message(client, napoli, text):
    response = schedule(client, napoli, text)

    assert response.status_code == 422
    assert response.json()["detail"] == INVALID_TIME


@pytest.mark.parametrize("style", ["offset", "z"])
def test_utc_delivery_times_are_converted_to_server_local_time(client, napoli, style):
    utc_text = DELIVERY.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    utc_text += "+00:00" if style == "offset" else "Z"

    response = schedule(client, napoli, utc_text)

    assert response.status_code == 201
    assert response.json()["scheduled_for"] == iso(DELIVERY)


# ---------------------------------------------------------------- opening hours at delivery time
@pytest.mark.parametrize(
    "when",
    ["2026-10-28T23:00:00",   # closing time is exclusive
     "2026-10-28T23:30:00",
     "2026-10-29T03:00:00",
     "2026-10-29T10:59:00"],
)
def test_delivery_time_when_restaurant_is_closed_is_rejected(client, napoli, when):
    response = schedule(client, napoli, when)

    assert response.status_code == 409
    assert "closed" in response.json()["detail"]


@pytest.mark.parametrize("when", ["2026-10-28T22:59:00", "2026-10-29T11:00:00"])
def test_delivery_time_at_the_edges_of_opening_hours_is_accepted(client, napoli, when):
    assert schedule(client, napoli, when).status_code == 201


def test_overnight_hours_are_respected(client, restaurants):
    taco = restaurants["Taco Libre"]  # 10:00-02:00

    assert schedule(client, taco, "2026-10-29T01:30:00").status_code == 201
    assert schedule(client, taco, "2026-10-29T03:00:00").status_code == 409


def test_24_hour_restaurant_accepts_any_delivery_time(client, restaurants):
    assert schedule(client, restaurants["Midnight Diner"], "2026-10-29T04:00:00").status_code == 201


def test_scheduling_is_allowed_while_the_restaurant_is_closed_now(client, clock, napoli):
    clock.now = datetime(2026, 10, 28, 3, 0)  # Napoli opens at 11:00

    response = schedule(client, napoli, "2026-10-28T12:00:00")

    assert response.status_code == 201
    assert response.json()["status"] == "scheduled"


# ---------------------------------------------------------------- release
def test_order_is_released_exactly_at_release_time_and_only_once(client, clock, scheduled_order):
    order_id = scheduled_order["id"]

    clock.now = RELEASE - timedelta(seconds=1)
    before = fetch(client, order_id)
    assert before["status"] == "scheduled" and before["released_at"] is None

    clock.now = RELEASE
    released = fetch(client, order_id)
    assert released["status"] == "placed"
    assert released["released_at"] == iso(RELEASE)

    clock.now = RELEASE + timedelta(minutes=10)
    assert fetch(client, order_id) == released  # not released again, nothing overwritten


def test_released_order_follows_the_normal_lifecycle(client, clock, scheduled_order):
    clock.now = RELEASE  # a status update sees the order as already released

    for status in ["confirmed", "preparing", "out_for_delivery", "delivered"]:
        response = set_status(client, scheduled_order["id"], status)
        assert response.status_code == 200
        assert response.json()["status"] == status


def test_clients_cannot_release_an_order_early(client, scheduled_order):
    response = set_status(client, scheduled_order["id"], "placed")

    assert response.status_code == 409
    assert fetch(client, scheduled_order["id"])["status"] == "scheduled"


def test_scheduled_order_cannot_skip_ahead_before_release(client, scheduled_order):
    response = set_status(client, scheduled_order["id"], "confirmed")

    assert response.status_code == 409
    assert fetch(client, scheduled_order["id"])["status"] == "scheduled"


def test_no_order_can_be_moved_back_to_scheduled(client, napoli):
    item = menu_of(client, napoli)[0]
    immediate = client.post("/orders", json={
        "restaurant_id": napoli["id"], "address": ADDRESS,
        "items": [{"menu_item_id": item["id"], "quantity": 1}],
    }).json()

    assert set_status(client, immediate["id"], "scheduled").status_code == 409


# ---------------------------------------------------------------- cancelling
def test_scheduled_order_can_be_cancelled_right_away(client, scheduled_order):
    response = set_status(client, scheduled_order["id"], "cancelled")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancelled_scheduled_order_is_never_released(client, clock, scheduled_order):
    clock.now = RELEASE - timedelta(seconds=1)
    assert set_status(client, scheduled_order["id"], "cancelled").status_code == 200

    clock.now = RELEASE + timedelta(hours=1)
    body = fetch(client, scheduled_order["id"])

    assert body["status"] == "cancelled"
    assert body["released_at"] is None


def test_after_release_the_order_is_cancellable_like_any_placed_order(client, clock, scheduled_order):
    clock.now = RELEASE

    response = set_status(client, scheduled_order["id"], "cancelled")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
