# AGENTS.md

Guidance for AI coding agents working on MiniDash, a small food-delivery REST API.

## Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI with SQLite (standard-library `sqlite3`), served by uvicorn
- **Tests:** pytest (`pytest` from the project root)
- **Run:** `uvicorn app.main:app --reload`

## Conventions

1. **Keep the layers one-way: `routes -> services -> repositories`.** Routes only parse requests and
   call a service. Business rules live in `services/` and `domain.py`. All SQL lives in
   `repositories/`. Services signal failures by raising `NotFoundError`, `ConflictError` or
   `UnprocessableError` from `errors.py`; never build HTTP responses outside `routes/` and `main.py`.

2. **Never read the real time directly.** Do not call `datetime.now()` or `time.time()` in app code.
   Use the injected clock (`create_app(clock=...)`, passed down as `now`). Tests move the fake clock
   in `tests/conftest.py` by hand and never sleep or depend on the time of day.

3. **Add no dependencies beyond `fastapi`, `uvicorn` and `pytest`.** That includes `httpx`, so API
   tests use the standard-library client in `tests/asgi_client.py` instead of `TestClient`. Every
   new endpoint or rule needs a test; money stays in integer cents.
