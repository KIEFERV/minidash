EXPECTED_FIELDS = {"id", "name", "cuisine", "opens_at", "closes_at", "avg_prep_minutes"}


def test_list_restaurants_returns_five_seeded(client):
    response = client.get("/restaurants")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert [r["id"] for r in body] == sorted(r["id"] for r in body)
    assert {r["name"] for r in body} == {
        "Napoli Slice", "Golden Wok", "Taco Libre", "Green Bowl", "Midnight Diner",
    }


def test_list_restaurants_has_expected_fields(client):
    for restaurant in client.get("/restaurants").json():
        assert set(restaurant) == EXPECTED_FIELDS
        assert isinstance(restaurant["avg_prep_minutes"], int)
        assert len(restaurant["opens_at"]) == 5  # "HH:MM"
        assert len(restaurant["closes_at"]) == 5


def test_menu_returns_items_for_that_restaurant_only(client, restaurants):
    seen_ids = set()
    for restaurant in restaurants.values():
        response = client.get(f"/restaurants/{restaurant['id']}/menu")

        assert response.status_code == 200
        menu = response.json()
        assert len(menu) == 5
        for item in menu:
            assert set(item) == {"id", "restaurant_id", "name", "price_cents"}
            assert item["restaurant_id"] == restaurant["id"]
            assert isinstance(item["price_cents"], int) and item["price_cents"] > 0
        seen_ids |= {item["id"] for item in menu}

    assert len(seen_ids) == 25  # no menu item is shared between restaurants


def test_menu_unknown_restaurant_returns_404(client):
    response = client.get("/restaurants/999/menu")

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


def test_menu_non_integer_id_returns_422(client):
    assert client.get("/restaurants/abc/menu").status_code == 422
