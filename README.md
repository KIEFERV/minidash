# MiniDash

A small food-delivery REST API built with **FastAPI** and **SQLite** (standard-library `sqlite3`).
Runtime/test dependencies are exactly `fastapi`, `uvicorn` and `pytest`. No authentication.

## Requirements

Python 3.10 or newer.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn app.main:app --reload
```

The API is now at <http://127.0.0.1:8000>, with interactive docs at <http://127.0.0.1:8000/docs>.

On first start the app creates `minidash.db` in the current directory and seeds 5 restaurants
with 5 menu items each. To start over, stop the server and delete `minidash.db`.
Set `MINIDASH_DB=/path/to/file.db` to use a different database file.

A database created by an earlier version is upgraded automatically on startup (new columns are
added, and the old `pending` status becomes `placed`).

## Endpoints

| Method | Path                      | Description                                      |
|--------|---------------------------|--------------------------------------------------|
| GET    | `/restaurants`            | List all restaurants                             |
| GET    | `/restaurants/{id}/menu`  | Menu items of one restaurant                     |
| POST   | `/orders`                 | Place an order now, or schedule one (201)        |
| GET    | `/orders/{id}`            | Fetch an order with its line items               |
| PATCH  | `/orders/{id}/status`     | Move an order to its next status, or cancel it   |

### Try it

```bash
curl http://127.0.0.1:8000/restaurants
curl http://127.0.0.1:8000/restaurants/5/menu

# order now (Midnight Diner is open 24 hours)
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id": 5, "address": "12 Main Street", "items": [{"menu_item_id": 21, "quantity": 2}]}'

# order now, deliver later (pick a time 45 minutes to 7 days from now)
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"restaurant_id": 5, "address": "12 Main Street", "items": [{"menu_item_id": 21, "quantity": 2}], "scheduled_for": "2026-11-02T18:30:00"}'

curl http://127.0.0.1:8000/orders/1

curl -X PATCH http://127.0.0.1:8000/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'
```

All money is in integer cents (`price_cents`, `total_cents`). All times are the server's local time.

## Scheduled orders

Add an optional `scheduled_for` (ISO 8601, e.g. `2026-11-02T18:30:00`) to `POST /orders` to order
now for delivery later.

* **Allowed window:** at least 45 minutes and at most 7 days from now (both bounds inclusive).
  Anything else, including text that is not a date and time, returns `422` with
  `{"detail": "Please enter a valid time"}`.
* **Opening hours:** the restaurant must be open at the delivery time, otherwise `409`. The restaurant
  does not need to be open at the moment you place the order.
* **Held, then released:** the order is created with status `scheduled`. Exactly 30 minutes before
  `scheduled_for` it is released to the restaurant and moves from `scheduled` to `placed`, once.
  `released_at` shows when that happened, and from then on it follows the normal lifecycle.
  Clients cannot release an order early; asking for `placed` returns `409`.
* **Cancelling:** `PATCH /orders/{id}/status` with `{"status": "cancelled"}` cancels a scheduled order
  before it is released, and a cancelled order is never released. After release the usual rule
  applies: it can still be cancelled until the restaurant starts preparing it.
* If you include a UTC offset or a trailing `Z` (`2026-11-02T18:30:00Z`), the time is converted to
  server-local time.

**How release works.** A background job runs every 30 seconds and releases every scheduled order that
is due. In addition, reading or updating an order (`GET /orders/{id}`, `PATCH .../status`) releases
that order first if its time has come, so what you see is correct even between job runs. Both paths
use one conditional `UPDATE ... WHERE status = 'scheduled'`, so an order is released at most once
however the two overlap.

### Business rules

* **Prices come from the menu.** The client sends only item ids and quantities; the total is
  computed on the server, and each line stores a snapshot of the unit price.
* **Opening hours are enforced** against the server's local time. Ordering immediately from a closed
  restaurant returns `409`. Hours are `"HH:MM"`; if `closes_at` is earlier than `opens_at` the
  restaurant is open overnight (Taco Libre, 10:00-02:00); if they are equal it is open 24 hours
  (Midnight Diner, handy for trying the API at any time of day).
* Repeated menu items in one order are merged into a single line. Every item must belong to
  the ordered restaurant (otherwise `422`).
* **Order status lifecycle** (anything else returns `409`):

  ```
  scheduled --(released automatically, 30 min before delivery)--> placed
                                                                    |
  placed -> confirmed -> preparing -> out_for_delivery -> delivered
     |          |
     +----------+--> cancelled      (until "preparing"; a scheduled order can also be cancelled)
  ```

  Orders placed without `scheduled_for` start as `placed`.

### Error responses

Errors have the shape `{"detail": ...}`: `404` unknown restaurant/order, `409` restaurant closed or
invalid status change, `422` invalid request body, items or delivery time.

## Project layout

```
app/
  main.py               app factory (injected clock, background job), error mapping
  dependencies.py       wires connection -> repositories -> services
  routes/               HTTP layer: parse requests, call a service, shape responses
  services/             business logic (totals, hours, scheduling, status transitions)
  repositories/         all SQL; return plain dicts
  scheduler.py          background loop that releases due scheduled orders
  schemas.py            request/response models
  domain.py             pure rules: OrderStatus, transitions, is_open(), scheduling window
  errors.py             NotFound / Conflict / Unprocessable
  database.py, seed.py  schema, migration, connections, demo data
tests/                  pytest suite
```

Dependencies point one way: `routes -> services -> repositories`.

## The clock

Nothing reads the system time directly. `create_app(db_path, clock=..., release_interval=...)` takes a
`clock` function (default `datetime.now`), and request handling, the opening-hours checks, the
scheduling window, `created_at` and the release job all use it. `release_interval=None` turns the
background job off.

## Run the tests

```bash
pytest
```

Each test gets its own temporary, freshly seeded database and a fake clock that the test moves by
hand, so the suite never touches `minidash.db`, never sleeps, and does not depend on the time of
day. The background loop is tested with an injected `sleep`.

FastAPI's `TestClient` requires `httpx`, which is outside this project's dependency list, so
`tests/asgi_client.py` provides a small standard-library ASGI client that sends requests
through the real application (including startup).
