from datetime import datetime

import pytest

from app.main import create_app
from tests.asgi_client import ASGIClient

# Wednesday noon: every seeded restaurant is open.
NOON = datetime(2026, 10, 28, 12, 0, 0)


class Clock:
    """Mutable fake clock. Tests change ``clock.now`` to move time."""

    def __init__(self):
        self.now = NOON


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def db_path(tmp_path) -> str:
    return str(tmp_path / "test.db")


@pytest.fixture
def client(db_path, clock):
    """A client on a fresh, freshly seeded database, driven by the fake clock.

    The background release job is off; tests move the clock and the app releases
    due orders when an order is read or updated (see test_release.py for the job).
    """
    app = create_app(db_path, clock=lambda: clock.now, release_interval=None)
    with ASGIClient(app) as c:
        yield c


@pytest.fixture
def restaurants(client) -> dict[str, dict]:
    """Seeded restaurants keyed by name."""
    return {r["name"]: r for r in client.get("/restaurants").json()}
