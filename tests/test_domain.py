from datetime import datetime, timedelta, timezone

import pytest

from app.domain import (
    OrderStatus,
    can_transition,
    is_open,
    is_valid_schedule_time,
    parse_scheduled_time,
    release_time,
)


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


# ---------------------------------------------------------------- status rules
def test_every_status_has_a_transition_rule():
    for status in OrderStatus:
        assert isinstance(can_transition(status, OrderStatus.CANCELLED), bool)


def test_clients_can_never_move_an_order_to_placed_or_scheduled():
    # SCHEDULED -> PLACED is done by the system only.
    for status in OrderStatus:
        assert not can_transition(status, OrderStatus.PLACED)
        assert not can_transition(status, OrderStatus.SCHEDULED)


def test_a_scheduled_order_can_only_be_cancelled_by_the_client():
    allowed = [s for s in OrderStatus if can_transition(OrderStatus.SCHEDULED, s)]
    assert allowed == [OrderStatus.CANCELLED]


# ---------------------------------------------------------------- scheduling rules
NOW = datetime(2026, 10, 28, 12, 0, 0)


@pytest.mark.parametrize(
    "offset, expected",
    [
        (timedelta(minutes=44, seconds=59), False),
        (timedelta(minutes=45), True),           # lower bound inclusive
        (timedelta(days=3), True),
        (timedelta(days=7), True),               # upper bound inclusive
        (timedelta(days=7, seconds=1), False),
        (timedelta(0), False),
        (timedelta(minutes=-5), False),
    ],
)
def test_is_valid_schedule_time(offset, expected):
    assert is_valid_schedule_time(NOW + offset, NOW) is expected


def test_release_time_is_30_minutes_before_delivery():
    assert release_time(datetime(2026, 10, 28, 18, 0)) == datetime(2026, 10, 28, 17, 30)


def test_parse_scheduled_time_accepts_iso_formats():
    expected = datetime(2026, 11, 2, 18, 30)
    assert parse_scheduled_time("2026-11-02T18:30:00") == expected
    assert parse_scheduled_time("2026-11-02 18:30") == expected
    assert parse_scheduled_time("  2026-11-02T18:30:00  ") == expected
    assert parse_scheduled_time("2026-11-02T18:30:00.789") == expected  # sub-second dropped


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "tomorrow", "2026-11-02", "02/11/2026 18:30", "2026-13-45T10:00:00", "T"],
)
def test_parse_scheduled_time_rejects_garbage(raw):
    assert parse_scheduled_time(raw) is None


@pytest.mark.parametrize("suffix", ["+00:00", "Z"])
def test_parse_scheduled_time_converts_offsets_to_server_local_time(suffix):
    local = datetime(2026, 10, 28, 14, 0)
    utc_text = local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + suffix
    assert parse_scheduled_time(utc_text) == local  # round trip, independent of machine timezone
