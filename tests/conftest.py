from datetime import datetime

import pytest

from app.dependencies import get_now
from app.main import create_app
from tests.asgi_client import ASGIClient

# Wednesday noon: every seeded restaurant is open.
NOON = datetime(2026, 10, 28, 12, 0, 0)


class Clock:
    """Mutable fake clock. Tests change ``clock.now`` to simulate other times."""

    def __init__(self):
        self.now = NOON


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def client(tmp_path, clock):
    """A client on a fresh, freshly seeded database in a temp directory."""
    app = create_app(str(tmp_path / "test.db"))
    app.dependency_overrides[get_now] = lambda: clock.now
    with ASGIClient(app) as c:
        yield c


@pytest.fixture
def restaurants(client) -> dict[str, dict]:
    """Seeded restaurants keyed by name."""
    return {r["name"]: r for r in client.get("/restaurants").json()}
