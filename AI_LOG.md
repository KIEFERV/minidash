## Entry 1

| Field | Entry |
|---|---|
| **Entry # / date** | 1 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 1: Injectable clock (refactor, no behaviour change) |
| **Prompt (verbatim or summarized)** | Verbatim (one prompt, reused for all 11 entries):<br>"Add a feature allowing customers to order now for delivery at a later point:<br>-Order accepts an optional scheduled delivery time. It must be at least 45 minutes and at most 7 days ahead; otherwise return "Please enter a valid time".<br>-Reject a scheduled time for when the restaraunt is closed<br>-A scheduled order is held and released to the restaraunt 30 minutes before it's delivery time, moving from SCHEDULED to PLACED exactly once<br>-User may cancel a scheduled order before it is released<br>-All time-dependent logic uses an injected clock so tests do not depend on real time"<br>Standing constraints from the original MiniDash request: layered structure (routes, services, repository), no authentication, no dependencies beyond fastapi, uvicorn and pytest. |
| **What the AI produced** | `create_app(db_path, clock=None, release_interval=30.0)` stores the clock on `app.state.clock`. `get_now(request)` in `dependencies.py` now returns `request.app.state.clock()` (it used to call `datetime.now()`, with tests overriding the dependency). `tests/conftest.py` rebuilt around a mutable fake `Clock` and `create_app(..., clock=lambda: clock.now, release_interval=None)`. `ASGIClient` now closes the default executor on exit.<br>Not requested: the `release_interval` parameter (belongs to slice 11, written in the same pass). |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** | None,First draft kept
| **Outcome** | Accepted

### Entry 2

| Field | Entry |
|---|---|
| **Entry # / date** | 2 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 2: Statuses and transitions |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “moving from SCHEDULED to PLACED exactly once” and “User may cancel a scheduled order before it is released”. |
| **What the AI produced** | `OrderStatus.SCHEDULED` added and `PENDING` renamed `PLACED` (stored value `pending` becomes `placed`). `ALLOWED_TRANSITIONS`: `scheduled` may only go to `cancelled`; no client request can reach `placed` or `scheduled`. Existing tests renamed from `pending` to `placed` with `sed`.<br>Not requested: the rename itself. The app used `pending`, the prompt said `PLACED`; the AI chose to unify them, which changes an API value. |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** |  None,First draft kept
| **Outcome** | Accepted


### Entry 3

| Field | Entry |
|---|---|
| **Entry # / date** | 3 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 3: Scheduling rules as pure functions |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “at least 45 minutes and at most 7 days ahead” and “released ... 30 minutes before”. |
| **What the AI produced** | In `domain.py`: `parse_scheduled_time`, `is_valid_schedule_time` (both bounds inclusive), `release_time`, and the constants `MIN_SCHEDULE_LEAD`, `MAX_SCHEDULE_LEAD`, `RELEASE_LEAD`. Tests added to `tests/test_domain.py`.<br>Not requested: UTC offset and `Z` conversion to server-local time, rejecting date-only strings, dropping fractional seconds. |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** | Small error with schedule timing;had to revise
| **Outcome** | Accepted


### Entry 4

| Field | Entry |
|---|---|
| **Entry # / date** | 4 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 4: Schema and migration |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: no bullet asks for this directly. It is needed to store the new status and times. |
| **What the AI produced** | Three nullable `orders` columns (`scheduled_for`, `release_at`, `released_at`), index `idx_orders_release`, and `_migrate()` called from `init_db` (adds missing columns, renames `pending` to `placed`, safe to repeat). `tests/test_migration.py` builds a first-version database.<br>Not requested: the whole migration (added so an existing `minidash.db` keeps working), and the stored `release_at` column (so due orders can be found with one query). |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** |  None,First draft kept
| **Outcome** | Accepted


### Entry 5

| Field | Entry |
|---|---|
| **Entry # / date** | 5 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 5: Create a scheduled order (happy path) |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “Order accepts an optional scheduled delivery time”. |
| **What the AI produced** | `OrderCreate.scheduled_for` and `OrderOut.scheduled_for` / `released_at`; the route passes the value on; `create_order(..., scheduled_for)` chooses `scheduled` or `placed`; the repository stores `scheduled_for` and `release_at` (delivery minus 30 minutes). Three tests in `test_scheduled_orders.py`.<br>Not requested: `scheduled_for` typed as a string (so bad values get the required message instead of FastAPI's default error), and `released_at` shown in responses. |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** |  None,First draft kept
| **Outcome** | Accepted


### Entry 6

| Field | Entry |
|---|---|
| **Entry # / date** | 6 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 6: Reject unusable delivery times |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “at least 45 minutes and at most 7 days ahead; otherwise return "Please enter a valid time"”. |
| **What the AI produced** | Service raises `UnprocessableError("Please enter a valid time")` (HTTP 422) for unparseable values and for times outside the window. Parametrised boundary tests in `test_scheduled_orders.py`.<br>Not requested: the status code (the prompt gave only the message), using the same message for unparseable input, and checking the window before opening hours. |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** |  None,First draft kept
| **Outcome** | Accepted

### Entry 7

| Field | Entry |
|---|---|
| **Entry # / date** | 7 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 7: Opening hours at the delivery time |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “Reject a scheduled time for when the restaraunt is closed”. |
| **What the AI produced** | Scheduled orders are checked with `is_open` at the delivery time; the "open right now" check now applies only to immediate orders. Closed at delivery time returns 409 with the restaurant's name and hours. Five tests in `test_scheduled_orders.py`.<br>Not requested: 409 as the status code, and allowing a scheduled order while the restaurant is closed right now. Only the delivery time is checked, not the release time (recorded as a known limitation in `design.md`). |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** |  None,First draft kept
| **Outcome** | Accepted

### Entry 8

| Field | Entry |
|---|---|
| **Entry # / date** | 8 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 8: Release due orders exactly once |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “released ... 30 minutes before it's delivery time, moving from SCHEDULED to PLACED exactly once”. |
| **What the AI produced** | `OrderRepository.release_due` (select due ids, then a conditional `UPDATE ... WHERE id = ? AND status = 'scheduled'` per id), `OrderService.release_due_orders()`, and a compare-and-set `update_status(order_id, expected, new)`. Four tests in `tests/test_release.py`.<br>Not requested: compare-and-set for every status update (this changed the repository method's signature), and oldest-release-time-first ordering. |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** | Small error where it wasn't working so I had to revise 
| **Outcome** | Accepted

### Entry 9

| Field | Entry |
|---|---|
| **Entry # / date** | 9 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 9: Release on read and update |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: the same release bullet. The prompt does not say when or how the release runs; this is the AI's interpretation. |
| **What the AI produced** | `get_order` and `update_status` first call `release_due(now, order_id)`, so a client never sees a stale `scheduled` after the release time. Two tests in `test_scheduled_orders.py`. The choice is recorded as option 1 of ADR-001 in `design.md`.<br>Not requested: the whole lazy-release path. A side effect is that a `GET` can write to the database when an order is due. |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** |  None,First draft kept
| **Outcome** | Accepted


### Entry 10

| Field | Entry |
|---|---|
| **Entry # / date** | 10 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 10: Cancel, and guard against manual release |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “User may cancel a scheduled order before it is released”. |
| **What the AI produced** | A scheduled order can be cancelled via `PATCH /orders/{id}/status`. Requesting `placed` returns 409 with a message that release is automatic; requesting `scheduled` is rejected; other statuses are rejected while `scheduled`. Six tests in `test_scheduled_orders.py`.<br>Not requested: my reading that cancelling after release is still allowed under the existing rules (the prompt only requires cancelling before release). |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** |  None,First draft kept
| **Outcome** | Accepted

### Entry 11

| Field | Entry |
|---|---|
| **Entry # / date** | 11 / Oct 29, 2026, [add time] |
| **Tool, model, mode** | Claude (Sonnet 5.5 per the app; confirm if you switched models), claude.ai chat with the code-execution sandbox. Not agent mode, no repo access, no network. FastAPI and pytest could not be installed there. |
| **Slice** | Slice 11: Background release loop and app lifecycle |
| **Prompt (verbatim or summarized)** | Same prompt as Entry 1. Relevant part: “released to the restaraunt 30 minutes before it's delivery time” (something has to trigger the release) and “tests do not depend on real time”. |
| **What the AI produced** | `app/scheduler.py` with `release_loop(release_once, interval, sleep)`: runs the release in a worker thread, logs and survives failures, `sleep` can be replaced in tests. The app lifespan starts it when `release_interval` is set and cancels it on shutdown; `release_once` opens its own connection. Three tests in `tests/test_release.py`.<br>Not requested: the background loop itself, the 30-second default, and the interval being settable only in code (not by environment variable). |
| **What I verified** | Ran pytest and tested in actual website.
| **What I changed and why** | None,First draft kept
| **Outcome** | Accepted
