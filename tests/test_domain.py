from datetime import datetime

import pytest

from app.domain import OrderStatus, can_transition, is_open


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 28, hour, minute)


@pytest.mark.parametrize(
    "opens, closes, now, expected",
    [
        ("11:00", "23:00", at(10, 59), False),
        ("11:00", "23:00", at(11, 0), True),    # opening time is inclusive
        ("11:00", "23:00", at(22, 59), True),
        ("11:00", "23:00", at(23, 0), False),   # closing time is exclusive
        ("10:00", "02:00", at(23, 30), True),   # overnight, before midnight
        ("10:00", "02:00", at(1, 59), True),    # overnight, after midnight
        ("10:00", "02:00", at(2, 0), False),
        ("10:00", "02:00", at(9, 59), False),
        ("00:00", "00:00", at(3, 0), True),     # 24 hours
    ],
)
def test_is_open(opens, closes, now, expected):
    assert is_open(opens, closes, now) is expected


def test_every_status_has_a_transition_rule():
    for status in OrderStatus:
        assert isinstance(can_transition(status, OrderStatus.PENDING), bool)


def test_nothing_can_move_back_to_pending():
    assert not any(can_transition(s, OrderStatus.PENDING) for s in OrderStatus)
