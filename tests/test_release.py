"""Release of scheduled orders below the HTTP layer, and the background job."""
import asyncio
from datetime import datetime, timedelta

import pytest

from app.database import connect, init_db
from app.domain import OrderStatus
from app.main import create_app
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.scheduler import release_loop
from app.services.order_service import OrderService
from tests.asgi_client import ASGIClient

NOON = datetime(2026, 10, 28, 12, 0, 0)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 28, hour, minute)


@pytest.fixture
def env(tmp_path):
    """A seeded database plus a factory for services bound to a chosen 'now'."""
    path = str(tmp_path / "release.db")
    init_db(path)
    conn = connect(path)
    orders, restaurants = OrderRepository(conn), RestaurantRepository(conn)

    class Env:
        repo = orders

        @staticmethod
        def service(now: datetime) -> OrderService:
            return OrderService(orders, restaurants, now)

        @staticmethod
        def schedule(delivery: datetime) -> dict:
            # Napoli Slice (id 1) is open 11:00-23:00; its first menu item is id 1.
            return Env.service(NOON).create_order(
                1, "12 Main Street", [(1, 1)], scheduled_for=delivery.isoformat()
            )

    yield Env
    conn.close()


# ---------------------------------------------------------------- release_due_orders
def test_each_due_order_is_released_once_and_only_when_due(env):
    first = env.schedule(at(14, 0))    # released 13:30
    second = env.schedule(at(14, 30))  # released 14:00
    immediate = env.service(NOON).create_order(1, "12 Main Street", [(1, 1)])

    assert env.service(at(13, 29)).release_due_orders() == []
    assert env.service(at(13, 30)).release_due_orders() == [first["id"]]
    assert env.service(at(13, 30)).release_due_orders() == []   # exactly once
    assert env.service(at(13, 59)).release_due_orders() == []
    assert env.service(at(14, 0)).release_due_orders() == [second["id"]]
    assert env.service(at(23, 0)).release_due_orders() == []

    later = env.service(at(23, 0))
    assert later.get_order(first["id"])["released_at"] == "2026-10-28T13:30:00"
    assert later.get_order(second["id"])["released_at"] == "2026-10-28T14:00:00"
    assert later.get_order(immediate["id"])["released_at"] is None
    assert later.get_order(immediate["id"])["status"] == "placed"


def test_overdue_orders_are_all_released_in_release_time_order(env):
    late = env.schedule(at(16, 0))
    early = env.schedule(at(14, 0))

    assert env.service(at(20, 0)).release_due_orders() == [early["id"], late["id"]]


def test_cancelled_scheduled_orders_are_never_released(env):
    order = env.schedule(at(14, 0))
    env.service(at(13, 0)).update_status(order["id"], OrderStatus.CANCELLED)

    assert env.service(at(15, 0)).release_due_orders() == []
    cancelled = env.service(at(15, 0)).get_order(order["id"])
    assert cancelled["status"] == "cancelled" and cancelled["released_at"] is None


def test_release_is_a_compare_and_set(env):
    order = env.schedule(at(14, 0))
    assert env.repo.release_due("2026-10-28T13:30:00") == [order["id"]]

    # A caller that still believes the order is SCHEDULED must not overwrite it.
    assert env.repo.update_status(order["id"], "scheduled", "cancelled") is False
    assert env.repo.get(order["id"])["status"] == "placed"
    # ...and a second release attempt does nothing.
    assert env.repo.release_due("2026-10-28T13:45:00") == []


# ---------------------------------------------------------------- background loop
def drive(release_once, ticks=3):
    """Run release_loop for ``ticks`` iterations using a fake sleep."""
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == ticks:
            raise asyncio.CancelledError  # stop the loop

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(release_loop(release_once, 30, sleep=fake_sleep))
    return sleeps


def test_release_loop_runs_every_interval():
    calls = []

    sleeps = drive(lambda: calls.append(1) or [])

    assert len(calls) == 3
    assert sleeps == [30, 30, 30]


def test_release_loop_survives_a_failing_run():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database is locked")
        return []

    drive(flaky)

    assert len(calls) == 3  # kept going after the first run failed


def test_app_starts_and_stops_cleanly_with_the_background_job_enabled(tmp_path):
    app = create_app(str(tmp_path / "job.db"), clock=lambda: NOON, release_interval=3600)

    with ASGIClient(app) as client:
        assert client.get("/restaurants").status_code == 200
