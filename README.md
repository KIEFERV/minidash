# MiniDash

A small food-delivery REST API built with **FastAPI** and **SQLite** (standard-library `sqlite3`).
Runtime/test dependencies are exactly `fastapi`, `uvicorn` and `pytest`. No authentication.

## Requirements

Python 3.10 or newer.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

The API is now at <http://127.0.0.1:8000>, with interactive docs at <http://127.0.0.1:8000/docs>.

On first start the app creates `minidash.db` in the current directory and seeds 5 restaurants
with 5 menu items each. To start over, stop the server and delete `minidash.db`.
Set `MINIDASH_DB=/path/to/file.db` to use a different database file.

## Endpoints

| Method | Path                      | Description                                      |
|--------|---------------------------|--------------------------------------------------|
| GET    | `/restaurants`            | List all restaurants                             |
| GET    | `/restaurants/{id}/menu`  | Menu items of one restaurant                     |
| POST   | `/orders`                 | Place an order (201)                             |
| GET    | `/orders/{id}`            | Fetch an order with its line items               |
| PATCH  | `/orders/{id}/status`     | Move an order to its next status                 |

### Try it

```bash
curl http://127.0.0.1:8000/restaurants
curl http://127.0.0.1:8000/restaurants/1/menu

curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id": 5, "address": "12 Main Street", "items": [{"menu_item_id": 21, "quantity": 2}]}'

curl http://127.0.0.1:8000/orders/1

curl -X PATCH http://127.0.0.1:8000/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'
```

All money is in integer cents (`price_cents`, `total_cents`).

### Business rules

* **Prices come from the menu.** The client sends only item ids and quantities; the total is
  computed on the server, and each line stores a snapshot of the unit price.
* **Opening hours are enforced** against the server's local time. Ordering from a closed
  restaurant returns `409`. Hours are `"HH:MM"`; if `closes_at` is earlier than `opens_at`
  the restaurant is open overnight (Taco Libre, 10:00-02:00); if they are equal it is open
  24 hours (Midnight Diner, handy for trying the API at any time of day).
* Repeated menu items in one order are merged into a single line. Every item must belong to
  the ordered restaurant (otherwise `422`).
* **Order status lifecycle** (anything else returns `409`):

  ```
  pending -> confirmed -> preparing -> out_for_delivery -> delivered
     \           \
      +-----------+--> cancelled      (only before "preparing")
  ```

### Error responses

Errors have the shape `{"detail": ...}`: `404` unknown restaurant/order, `409` restaurant closed or
invalid status change, `422` invalid request body or items.

## Project layout

```
app/
  main.py               app factory, startup (DB init + seed), error mapping
  dependencies.py       wires connection -> repositories -> services
  routes/               HTTP layer: parse requests, call a service, shape responses
  services/             business logic (totals, opening hours, status transitions)
  repositories/         all SQL; return plain dicts
  schemas.py            request/response models
  domain.py             pure rules: OrderStatus, transitions, is_open()
  errors.py             NotFound / Conflict / Unprocessable
  database.py, seed.py  schema, connections, demo data
tests/                  pytest suite
```

Dependencies point one way: `routes -> services -> repositories`.

## Run the tests

```bash
pytest
```

Each test gets its own temporary, freshly seeded database and a controllable fake clock, so
the suite never touches `minidash.db` and does not depend on the time of day.

FastAPI's `TestClient` requires `httpx`, which is outside this project's dependency list, so
`tests/asgi_client.py` provides a small standard-library ASGI client that sends requests
through the real application (including startup).
