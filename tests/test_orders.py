from datetime import datetime

import pytest

ADDRESS = "12 Main Street, Apt 4"


def menu_of(client, restaurant) -> list[dict]:
    return client.get(f"/restaurants/{restaurant['id']}/menu").json()


def place_order(client, restaurant, items, address=ADDRESS):
    return client.post(
        "/orders",
        json={"restaurant_id": restaurant["id"], "address": address, "items": items},
    )


@pytest.fixture
def napoli(restaurants):
    return restaurants["Napoli Slice"]


@pytest.fixture
def napoli_menu(client, napoli):
    return menu_of(client, napoli)


@pytest.fixture
def order(client, napoli, napoli_menu):
    """A freshly placed (placed) order."""
    response = place_order(client, napoli, [{"menu_item_id": napoli_menu[0]["id"], "quantity": 1}])
    assert response.status_code == 201
    return response.json()


def set_status(client, order_id, status):
    return client.patch(f"/orders/{order_id}/status", json={"status": status})


# ---------------------------------------------------------------- POST /orders
def test_create_order_returns_201_with_computed_total(client, napoli, napoli_menu):
    first, second = napoli_menu[0], napoli_menu[1]

    response = place_order(client, napoli, [
        {"menu_item_id": first["id"], "quantity": 2},
        {"menu_item_id": second["id"], "quantity": 1},
    ])

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "placed"
    assert body["restaurant_id"] == napoli["id"]
    assert body["address"] == ADDRESS
    assert body["total_cents"] == 2 * first["price_cents"] + second["price_cents"]
    assert body["created_at"] == "2026-10-28T12:00:00"
    assert body["items"] == [
        {"menu_item_id": first["id"], "name": first["name"], "quantity": 2,
         "unit_price_cents": first["price_cents"]},
        {"menu_item_id": second["id"], "name": second["name"], "quantity": 1,
         "unit_price_cents": second["price_cents"]},
    ]


def test_create_order_merges_duplicate_items(client, napoli, napoli_menu):
    item = napoli_menu[0]

    response = place_order(client, napoli, [
        {"menu_item_id": item["id"], "quantity": 1},
        {"menu_item_id": item["id"], "quantity": 2},
    ])

    body = response.json()
    assert response.status_code == 201
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 3
    assert body["total_cents"] == 3 * item["price_cents"]


def test_create_order_trims_address(client, napoli, napoli_menu):
    response = place_order(
        client, napoli, [{"menu_item_id": napoli_menu[0]["id"], "quantity": 1}],
        address="   99 Oak Ave  ",
    )

    assert response.status_code == 201
    assert response.json()["address"] == "99 Oak Ave"


def test_create_order_unknown_restaurant_returns_404(client):
    response = client.post(
        "/orders",
        json={"restaurant_id": 999, "address": ADDRESS,
              "items": [{"menu_item_id": 1, "quantity": 1}]},
    )

    assert response.status_code == 404


def test_create_order_unknown_menu_item_returns_422(client, napoli):
    response = place_order(client, napoli, [{"menu_item_id": 9999, "quantity": 1}])

    assert response.status_code == 422
    assert "9999" in response.json()["detail"]


def test_create_order_item_from_another_restaurant_returns_422(client, napoli, restaurants):
    other_item = menu_of(client, restaurants["Golden Wok"])[0]

    response = place_order(client, napoli, [{"menu_item_id": other_item["id"], "quantity": 1}])

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"restaurant_id": 1, "address": ADDRESS, "items": []},
        {"restaurant_id": 1, "address": ADDRESS},
        {"restaurant_id": 1, "items": [{"menu_item_id": 1, "quantity": 1}]},
        {"restaurant_id": 1, "address": "   ", "items": [{"menu_item_id": 1, "quantity": 1}]},
        {"restaurant_id": 1, "address": ADDRESS, "items": [{"menu_item_id": 1, "quantity": 0}]},
        {"restaurant_id": 1, "address": ADDRESS, "items": [{"menu_item_id": 1, "quantity": -2}]},
        {"restaurant_id": 1, "address": ADDRESS, "items": [{"menu_item_id": 1, "quantity": 51}]},
        {"restaurant_id": "abc", "address": ADDRESS, "items": [{"menu_item_id": 1, "quantity": 1}]},
        {"address": ADDRESS, "items": [{"menu_item_id": 1, "quantity": 1}]},
    ],
    ids=[
        "empty-items", "missing-items", "missing-address", "blank-address",
        "zero-quantity", "negative-quantity", "quantity-too-large",
        "restaurant-id-not-int", "missing-restaurant-id",
    ],
)
def test_create_order_rejects_invalid_payload(client, payload):
    assert client.post("/orders", json=payload).status_code == 422


def test_create_order_when_restaurant_closed_returns_409(client, clock, napoli, napoli_menu):
    clock.now = datetime(2026, 10, 28, 3, 0)  # Napoli Slice opens at 11:00

    response = place_order(client, napoli, [{"menu_item_id": napoli_menu[0]["id"], "quantity": 1}])

    assert response.status_code == 409
    assert "closed" in response.json()["detail"]


def test_create_order_at_overnight_restaurant_after_midnight(client, clock, restaurants):
    taco = restaurants["Taco Libre"]  # 10:00-02:00
    item = menu_of(client, taco)[0]
    clock.now = datetime(2026, 10, 29, 1, 0)

    response = place_order(client, taco, [{"menu_item_id": item["id"], "quantity": 1}])

    assert response.status_code == 201


def test_create_order_at_24_hour_restaurant_in_the_small_hours(client, clock, restaurants):
    diner = restaurants["Midnight Diner"]  # opens_at == closes_at
    item = menu_of(client, diner)[0]
    clock.now = datetime(2026, 10, 29, 3, 30)

    response = place_order(client, diner, [{"menu_item_id": item["id"], "quantity": 1}])

    assert response.status_code == 201


# ---------------------------------------------------------------- GET /orders/{id}
def test_get_order_returns_the_created_order(client, order):
    response = client.get(f"/orders/{order['id']}")

    assert response.status_code == 200
    assert response.json() == order


def test_get_order_unknown_id_returns_404(client):
    response = client.get("/orders/12345")

    assert response.status_code == 404


def test_get_order_non_integer_id_returns_422(client):
    assert client.get("/orders/abc").status_code == 422


# ---------------------------------------------------------------- PATCH /orders/{id}/status
def test_patch_status_walks_the_full_lifecycle(client, order):
    for status in ["confirmed", "preparing", "out_for_delivery", "delivered"]:
        response = set_status(client, order["id"], status)

        assert response.status_code == 200
        assert response.json()["status"] == status

    # The change is persisted and the rest of the order is untouched.
    fetched = client.get(f"/orders/{order['id']}").json()
    assert fetched["status"] == "delivered"
    assert fetched["total_cents"] == order["total_cents"]
    assert fetched["items"] == order["items"]


def test_patch_status_can_cancel_a_placed_order(client, order):
    response = set_status(client, order["id"], "cancelled")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_patch_status_cannot_skip_steps(client, order):
    response = set_status(client, order["id"], "delivered")

    assert response.status_code == 409
    assert client.get(f"/orders/{order['id']}").json()["status"] == "placed"


def test_patch_status_cannot_cancel_once_preparing(client, order):
    set_status(client, order["id"], "confirmed")
    set_status(client, order["id"], "preparing")

    assert set_status(client, order["id"], "cancelled").status_code == 409


def test_patch_status_terminal_states_cannot_change(client, order):
    set_status(client, order["id"], "cancelled")

    assert set_status(client, order["id"], "confirmed").status_code == 409


def test_patch_status_to_same_status_returns_409(client, order):
    assert set_status(client, order["id"], "placed").status_code == 409


def test_patch_status_unknown_status_value_returns_422(client, order):
    assert set_status(client, order["id"], "teleported").status_code == 422


def test_patch_status_missing_body_returns_422(client, order):
    assert client.patch(f"/orders/{order['id']}/status").status_code == 422


def test_patch_status_unknown_order_returns_404(client):
    assert set_status(client, 12345, "confirmed").status_code == 404
