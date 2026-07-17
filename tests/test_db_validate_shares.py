"""Unit tests for db.validate_shares() -- the sum-to-1.0 guard reused by
db.assign_item() (schema.sql: "La suma de share para un mismo item_id debe
ser 1.0")."""

import pytest


def test_exact_one_passes(local_db):
    # Must not raise.
    local_db.validate_shares([1.0])
    local_db.validate_shares([1 / 3, 1 / 3, 1 / 3])
    local_db.validate_shares([0.5, 0.5])


def test_sum_below_one_raises(local_db):
    with pytest.raises(ValueError, match="must sum to 1.0"):
        local_db.validate_shares([0.9])


def test_sum_above_one_raises(local_db):
    with pytest.raises(ValueError, match="must sum to 1.0"):
        local_db.validate_shares([1.1])


@pytest.mark.parametrize(
    "shares",
    [
        [0.3, 0.3, 0.3],  # 0.9
        [0.5, 0.6],  # 1.1
        [0.25, 0.25, 0.25],  # 0.75
    ],
)
def test_various_non_summing_combinations_raise(local_db, shares):
    with pytest.raises(ValueError):
        local_db.validate_shares(shares)


def test_tolerance_boundary_just_inside_passes(local_db):
    # 1e-6 is the exact tolerance in db.py's `abs(total - 1.0) > 1e-6`.
    # A deviation of 9e-7 is strictly inside the tolerance -> must pass.
    local_db.validate_shares([1.0 + 9e-7])


def test_tolerance_boundary_just_outside_raises(local_db):
    # A deviation of 2e-6 is strictly outside the tolerance -> must raise.
    with pytest.raises(ValueError):
        local_db.validate_shares([1.0 + 2e-6])
