'''Phase 5 tests: money/precision and UTC time helpers.'''

from __future__ import annotations

from datetime import timezone

import pytest

from ccbalancer.utils import money, timeutil


@pytest.mark.parametrize(
    'value, expected',
    [
        (None, None),
        (3, 3),
        (0, 0),
        (0.001, 3),
        (0.5, 1),
        (1.0, 0),
        (10.0, 0),
    ],
)
def test_precision_to_decimals(value, expected):
    assert money.precision_to_decimals(value) == expected


def test_round_amount_floors_to_precision():
    assert money.round_amount(0.123456, 3) == 0.123


def test_round_amount_passthrough_when_unknown():
    assert money.round_amount(0.123456, None) == 0.123456


def test_notional_uses_decimal_precision():
    assert money.notional(0.1, 50000.0) == 5000.0


def test_now_iso_ends_with_z():
    stamp = timeutil.now_iso()
    assert stamp.endswith('Z')
    assert timeutil.parse_iso(stamp).tzinfo == timezone.utc


def test_parse_iso_assumes_utc_for_naive():
    parsed = timeutil.parse_iso('2026-06-18T12:00:00')
    assert parsed.tzinfo == timezone.utc


def test_parse_iso_converts_offset_to_utc():
    parsed = timeutil.parse_iso('2026-06-18T14:00:00+02:00')
    assert parsed.hour == 12
    assert parsed.tzinfo == timezone.utc


def test_hours_between():
    start = '2026-06-18T00:00:00Z'
    end = '2026-06-18T06:30:00Z'
    assert timeutil.hours_between(start, end) == 6.5
