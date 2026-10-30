# Tasks: Scheduled orders

| | |
|---|---|
| **Status** | All slices implemented; follow-ups at the end are proposed |
| **Date** | 2026-10-29 |
| **Requirements** | [requirements.md](requirements.md) |
| **Design** | [design.md](design.md) |

Each slice is small enough to build and test on its own, and each leaves the suite green. They are
ordered so that every slice only depends on earlier ones. Test names are in `tests/`; `file::name`
means a test function in that file, and "(param)" means a parametrised test.

## Verification status

As of 2026-10-29 the domain, migration, release-logic and background-loop tests were executed in the
authoring environment (37 test cases passed, using a small stand-in for pytest because pytest and
FastAPI could not be installed there). **Not yet executed:** every test that goes through HTTP
(`test_scheduled_orders.py`, `test_orders.py`, `test_restaurants.py`) and
`test_release.py::test_app_starts_and_stops_cleanly_with_the_background_job_enabled`. Run `pytest`
to confirm them.

## Slices

### Slice 1: Injectable clock (refactor, no behaviour change)
- [x] `create_app(db_path, clock=None, release_interval=...)` stores the clock in `app.state.clock`; `get_now` reads it; `conftest.py` builds the app with a fake `Clock` and `release_interval=None`.
- **Requirements:** 6.1, 6.2, 6.3
- **Verified by:** `test_orders.py::test_create_order_returns_201_with_computed_total` (`created_at` equals the fake clock's noon) and `test_orders.py::test_create_order_when_restaurant_closed_returns_409` (moving the fake clock to 03:00 closes the restaurant).
- **Done when:** the existing order and restaurant tests pass with no use of the real time.

### Slice 2: Statuses and transitions
- [x] Add `SCHEDULED`, rename `PENDING` to `PLACED`; transition table lets `scheduled` go only to `cancelled`; nothing may be moved to `scheduled` or `placed` by a client.
- **Requirements:** 5.3, 5.5
- **Verified by:** `test_domain.py::test_clients_can_never_move_an_order_to_placed_or_scheduled`, `test_domain.py::test_a_scheduled_order_can_only_be_cancelled_by_the_client`, `test_domain.py::test_every_status_has_a_transition_rule`; existing lifecycle tests in `test_orders.py` updated from `pending` to `placed` (for example `test_patch_status_walks_the_full_lifecycle`).
- **Done when:** the pure domain tests pass and the renamed lifecycle tests pass.

### Slice 3: Scheduling rules as pure functions
- [x] `parse_scheduled_time`, `is_valid_schedule_time`, `release_time` and the three duration constants in `domain.py`.
- **Requirements:** 1.5, 1.6, 2.1, 2.2, 2.3, 2.4, 4.2
- **Verified by:** `test_domain.py::test_is_valid_schedule_time` (param: 44:59 rejected, 45:00 accepted, 7 days accepted, 7 days plus 1 s rejected, now and past rejected), `test_parse_scheduled_time_accepts_iso_formats`, `test_parse_scheduled_time_rejects_garbage` (param), `test_parse_scheduled_time_converts_offsets_to_server_local_time` (param), `test_release_time_is_30_minutes_before_delivery`.
- **Done when:** all of the above pass with no database or web framework involved.

### Slice 4: Schema and migration
- [x] Three new `orders` columns, `_migrate()` (add missing columns, rename `pending`, create the release index), called from `init_db`.
- **Requirements:** 7.1, 7.2, 7.3, 7.4
- **Verified by:** `test_migration.py::test_old_database_gains_new_columns_and_status_name` (builds a first-version database, runs `init_db` twice, checks columns, statuses and that nothing is re-seeded).
- **Done when:** the test passes and a fresh database still seeds five restaurants (`test_restaurants.py::test_list_restaurants_returns_five_seeded`).

### Slice 5: Create a scheduled order (happy path)
- [x] `OrderCreate.scheduled_for`; `OrderOut.scheduled_for` and `released_at`; route passes the value; service picks `scheduled` or `placed`; repository stores `scheduled_for` and `release_at`; offsets converted to local time.
- **Requirements:** 1.1, 1.2, 1.3, 1.4, 1.5
- **Verified by:** `test_scheduled_orders.py::test_scheduled_order_is_held_as_scheduled`, `::test_order_without_a_schedule_is_placed_immediately` (param: field omitted and field null), `::test_utc_delivery_times_are_converted_to_server_local_time` (param: `+00:00` and `Z`).
- **Done when:** a scheduled order comes back with status `scheduled`, the right total, `scheduled_for` and `released_at` null, while immediate orders still come back `placed`.

### Slice 6: Reject unusable delivery times
- [x] Service raises `Please enter a valid time` (`422`) for unparseable values and values outside 45 minutes to 7 days.
- **Requirements:** 2.1, 2.2, 2.3, 2.4
- **Verified by:** `test_scheduled_orders.py::test_delivery_time_must_be_45_minutes_to_7_days_ahead` (param: exactly 45 min, 44:59, 10 min, now, past, exactly 7 days, 7 days plus 1 s) and `::test_unparseable_delivery_time_returns_the_same_message` (param).
- **Done when:** boundaries are inclusive and every rejection carries exactly the required message.

### Slice 7: Opening hours at the delivery time
- [x] Scheduled orders are checked against opening hours at the delivery time; the "open now" check applies only to immediate orders.
- **Requirements:** 1.7, 3.1, 3.2, 3.3, 3.4
- **Verified by:** `test_scheduled_orders.py::test_delivery_time_when_restaurant_is_closed_is_rejected` (param), `::test_delivery_time_at_the_edges_of_opening_hours_is_accepted` (param), `::test_overnight_hours_are_respected`, `::test_24_hour_restaurant_accepts_any_delivery_time`, `::test_scheduling_is_allowed_while_the_restaurant_is_closed_now`; `test_domain.py::test_is_open` (param).
- **Done when:** closing time is exclusive, opening time inclusive, overnight and 24-hour restaurants behave, and ordering ahead works while the restaurant is closed.

### Slice 8: Release due orders exactly once
- [x] `OrderRepository.release_due` (conditional `UPDATE ... WHERE status = 'scheduled'`), `OrderService.release_due_orders`, and compare-and-set `update_status`.
- **Requirements:** 4.2, 4.3, 5.2, 5.7
- **Verified by:** `test_release.py::test_each_due_order_is_released_once_and_only_when_due`, `::test_overdue_orders_are_all_released_in_release_time_order`, `::test_cancelled_scheduled_orders_are_never_released`, `::test_release_is_a_compare_and_set`.
- **Done when:** a second release finds nothing to do, immediate orders are untouched, and a stale `scheduled -> cancelled` update fails after a release.

### Slice 9: Release on read and update
- [x] `get_order` and `update_status` call `release_due(now, order_id)` first.
- **Requirements:** 4.1, 4.2, 4.3, 4.6, 4.8
- **Verified by:** `test_scheduled_orders.py::test_order_is_released_exactly_at_release_time_and_only_once` (one second before: `scheduled`; at release time: `placed` with `released_at`; later: unchanged) and `::test_released_order_follows_the_normal_lifecycle` (confirm right at the release time works).
- **Done when:** the status read back never lags the fake clock, and `released_at` is never overwritten.

### Slice 10: Cancel, and guard against manual release
- [x] A scheduled order can be cancelled; `placed` and `scheduled` cannot be requested by clients; other statuses are rejected while `scheduled`.
- **Requirements:** 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
- **Verified by:** `test_scheduled_orders.py::test_scheduled_order_can_be_cancelled_right_away`, `::test_cancelled_scheduled_order_is_never_released`, `::test_clients_cannot_release_an_order_early`, `::test_scheduled_order_cannot_skip_ahead_before_release`, `::test_no_order_can_be_moved_back_to_scheduled`, `::test_after_release_the_order_is_cancellable_like_any_placed_order`.
- **Done when:** a cancelled order stays cancelled with `released_at` null after the release time passes.

### Slice 11: Background release loop and app lifecycle
- [x] `scheduler.release_loop` (runs `release_once` in a worker thread, logs and survives failures, injectable `sleep`); lifespan starts it when `release_interval` is set and cancels it on shutdown.
- **Requirements:** 4.4, 4.5, 4.7, 6.3, 6.4
- **Verified by:** `test_release.py::test_release_loop_runs_every_interval`, `::test_release_loop_survives_a_failing_run`, `::test_app_starts_and_stops_cleanly_with_the_background_job_enabled`.
- **Done when:** the loop calls the release once per tick with no real waiting, a raised error does not stop it, and the app starts and stops cleanly with the job enabled.

## Follow-up slices (gaps in coverage)

Not part of the implementation above. These close the "Not covered" and "Partial" rows in the
requirements traceability table.

| # | Slice | Test to add | Closes |
|---|---|---|---|
| F1 | Window error wins over closed error | Create a scheduled order for a time that is both over 7 days away and outside opening hours; expect `422` and `Please enter a valid time`. | 2.5 |
| F2 | Closed message content | Assert the `409` detail contains the restaurant name, "closed at the requested delivery time" and its hours. | 3.1 |
| F3 | Release message content | Assert the `409` detail for `PATCH ... placed` on a scheduled order explains automatic release. | 5.4 |
| F4 | Lost update surfaces as `409` | At service level, make `OrderRepository.update_status` return `False` (for example with a stub) and expect `ConflictError`. | 5.7 |
| F5 | Default job interval | Assert the default `release_interval` of `create_app` is 30 seconds. | 4.4 |
| F6 | Catch-up at startup | Create an overdue scheduled order in a database, start the app with the job enabled and the fake clock past the release time, then assert it is `placed` without any `GET` or `PATCH`. | 4.5 |
| F7 | Failure is logged | Use pytest's `caplog` in `test_release_loop_survives_a_failing_run` to assert an error record. | 4.7 |
| F8 | Run the HTTP-level tests | Run `pytest` and fix anything that fails. | Verification status |