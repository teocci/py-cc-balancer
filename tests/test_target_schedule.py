'''I-17 tests: the external target-schedule loader and lookup.

Pure, no network: a JSONL path in, a validated forward-filled step function out.
Covers the bisect lookup, start-coverage check, a stable digest, and every
validation failure (empty, malformed JSON, missing keys, out-of-range target,
non-increasing dates).
'''

from __future__ import annotations

import pytest

from ccbalancer.exceptions import StateError
from ccbalancer.stores.target_schedule import TargetSchedule, load_target_schedule

_DAY_MS = 86_400_000
_START = 1_661_990_400_000  # 2022-09-01T00:00:00Z


def _write(tmp_path, *lines: str, name: str = 'schedule.jsonl'):
    path = tmp_path / name
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def test_load_parses_and_forward_fills(tmp_path):
    path = _write(
        tmp_path,
        '{"date": "2022-09-01", "target_volatile_pct": 90.0}',
        '{"date": "2022-09-05", "target_volatile_pct": 60.0}',
    )
    schedule = load_target_schedule(path)

    assert len(schedule.steps) == 2
    # Before the first step -> None (caller applies the pair's configured target).
    assert schedule.target_at(_START - _DAY_MS) is None
    # At/after the first step, and forward-filled until the next.
    assert schedule.target_at(_START) == 90.0
    assert schedule.target_at(_START + 3 * _DAY_MS) == 90.0
    assert schedule.target_at(_START + 4 * _DAY_MS) == 60.0
    assert schedule.target_at(_START + 100 * _DAY_MS) == 60.0


def test_covers_start(tmp_path):
    path = _write(tmp_path, '{"date": "2022-09-05", "target_volatile_pct": 60.0}')
    schedule = load_target_schedule(path)
    assert schedule.covers_start(_START + 10 * _DAY_MS) is True   # start after the step
    assert schedule.covers_start(_START) is False                # start before the step


def test_digest_is_stable_and_distinct(tmp_path):
    a = load_target_schedule(_write(tmp_path, '{"date": "2022-09-01", "target_volatile_pct": 90.0}', name='a'))
    b = load_target_schedule(_write(tmp_path, '{"date": "2022-09-01", "target_volatile_pct": 90.0}', name='b'))
    c = load_target_schedule(_write(tmp_path, '{"date": "2022-09-01", "target_volatile_pct": 60.0}', name='c'))
    assert a.digest() == b.digest()      # same content -> same digest
    assert a.digest() != c.digest()      # different target -> different digest


def test_blank_lines_are_ignored(tmp_path):
    path = tmp_path / 's.jsonl'
    path.write_text('\n{"date": "2022-09-01", "target_volatile_pct": 90.0}\n\n', encoding='utf-8')
    assert len(load_target_schedule(path).steps) == 1


def test_empty_file_rejected(tmp_path):
    path = tmp_path / 'empty.jsonl'
    path.write_text('\n\n', encoding='utf-8')
    with pytest.raises(StateError, match='empty'):
        load_target_schedule(path)


def test_missing_file_rejected(tmp_path):
    with pytest.raises(StateError, match='Cannot read'):
        load_target_schedule(tmp_path / 'nope.jsonl')


def test_malformed_json_rejected(tmp_path):
    with pytest.raises(StateError, match='not valid JSON'):
        load_target_schedule(_write(tmp_path, '{not json}'))


def test_missing_keys_rejected(tmp_path):
    with pytest.raises(StateError, match='date.*target_volatile_pct'):
        load_target_schedule(_write(tmp_path, '{"date": "2022-09-01"}'))


@pytest.mark.parametrize('pct', [-1.0, 100.1, 250.0])
def test_out_of_range_target_rejected(tmp_path, pct):
    with pytest.raises(StateError, match='out of range'):
        load_target_schedule(_write(tmp_path, f'{{"date": "2022-09-01", "target_volatile_pct": {pct}}}'))


def test_non_numeric_target_rejected(tmp_path):
    with pytest.raises(StateError, match='must be a number'):
        load_target_schedule(_write(tmp_path, '{"date": "2022-09-01", "target_volatile_pct": "high"}'))


@pytest.mark.parametrize('second_date', ['2022-09-01', '2022-08-31'])
def test_non_increasing_dates_rejected(tmp_path, second_date):
    with pytest.raises(StateError, match='strictly increasing'):
        load_target_schedule(_write(
            tmp_path,
            '{"date": "2022-09-01", "target_volatile_pct": 90.0}',
            f'{{"date": "{second_date}", "target_volatile_pct": 60.0}}',
        ))


def test_target_schedule_constructible_directly():
    schedule = TargetSchedule(((_START, 40.0), (_START + _DAY_MS, 55.0)))
    assert schedule.target_at(_START) == 40.0
    assert schedule.target_at(_START + _DAY_MS) == 55.0
