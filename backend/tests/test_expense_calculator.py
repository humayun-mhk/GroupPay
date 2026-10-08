from decimal import Decimal

import pytest

from app.models.expense import SplitType
from app.services.balances import simplify_debts
from app.services.expense_calculator import SplitInput, SplitValidationError, calculate_split


def allocations(total, split_type, entries):
    return {
        item.user_id: item.amount_owed
        for item in calculate_split(Decimal(total), split_type, entries)
    }


def test_equal_split_allocates_exactly():
    assert allocations("4000.00", SplitType.EQUAL, [SplitInput(i) for i in [4, 3, 2, 1]]) == {
        1: Decimal("1000.00"),
        2: Decimal("1000.00"),
        3: Decimal("1000.00"),
        4: Decimal("1000.00"),
    }
    five_way = allocations("5000.00", SplitType.EQUAL, [SplitInput(i) for i in [5, 4, 3, 2, 1]])
    assert set(five_way.values()) == {Decimal("1000.00")}


def test_uneven_equal_split_uses_deterministic_cent_remainders():
    entries = [SplitInput(3), SplitInput(1), SplitInput(2)]
    expected = {1: Decimal("3.34"), 2: Decimal("3.33"), 3: Decimal("3.33")}
    assert allocations("10.00", SplitType.EQUAL, entries) == expected
    assert allocations("10.00", SplitType.EQUAL, entries) == expected


def test_exact_split_and_invalid_exact_total():
    exact = [
        SplitInput(1, amount=Decimal("500")),
        SplitInput(2, amount=Decimal("1500")),
        SplitInput(3, amount=Decimal("1000")),
    ]
    assert allocations("3000", SplitType.EXACT, exact) == {
        1: Decimal("500.00"),
        2: Decimal("1500.00"),
        3: Decimal("1000.00"),
    }
    with pytest.raises(SplitValidationError, match="must total"):
        calculate_split(
            Decimal("3000"),
            SplitType.EXACT,
            [SplitInput(1, amount=Decimal("500")), SplitInput(2, amount=Decimal("500"))],
        )


def test_percentage_split_and_invalid_total():
    entries = [
        SplitInput(1, percentage=Decimal("50")),
        SplitInput(2, percentage=Decimal("30")),
        SplitInput(3, percentage=Decimal("20")),
    ]
    assert allocations("4000", SplitType.PERCENTAGE, entries) == {
        1: Decimal("2000.00"),
        2: Decimal("1200.00"),
        3: Decimal("800.00"),
    }
    with pytest.raises(SplitValidationError, match="100"):
        calculate_split(
            Decimal("4000"),
            SplitType.PERCENTAGE,
            [SplitInput(1, percentage=Decimal("60")), SplitInput(2, percentage=Decimal("30"))],
        )


def test_share_split_and_invalid_share():
    entries = [
        SplitInput(1, shares=Decimal("2")),
        SplitInput(2, shares=Decimal("1")),
        SplitInput(3, shares=Decimal("1")),
    ]
    assert allocations("4000", SplitType.SHARES, entries) == {
        1: Decimal("2000.00"),
        2: Decimal("1000.00"),
        3: Decimal("1000.00"),
    }
    with pytest.raises(SplitValidationError, match="positive"):
        calculate_split(Decimal("4000"), SplitType.SHARES, [SplitInput(1, shares=Decimal("0"))])


@pytest.mark.parametrize("total", ["0", "-1", "0.001"])
def test_zero_negative_and_subcent_expense_totals_are_rejected(total):
    with pytest.raises(SplitValidationError):
        calculate_split(Decimal(total), SplitType.EQUAL, [SplitInput(1)])


def test_duplicate_and_empty_participants_are_rejected():
    with pytest.raises(SplitValidationError, match="duplicated"):
        calculate_split(Decimal("10"), SplitType.EQUAL, [SplitInput(1), SplitInput(1)])
    with pytest.raises(SplitValidationError, match="At least one"):
        calculate_split(Decimal("10"), SplitType.EQUAL, [])


def test_simplification_nets_a_chain_to_one_transfer():
    assert simplify_debts({1: Decimal("-1000.00"), 2: Decimal("0.00"), 3: Decimal("1000.00")}) == [
        (1, 3, Decimal("1000.00"))
    ]


def test_complex_settlements_are_deterministic_and_clear_every_balance():
    original = {
        1: Decimal("-90.00"),
        2: Decimal("-10.00"),
        3: Decimal("40.00"),
        4: Decimal("60.00"),
        5: Decimal("0.00"),
    }
    suggested = simplify_debts(original)
    assert suggested == simplify_debts(original)
    resulting = dict(original)
    for debtor, creditor, amount in suggested:
        resulting[debtor] += amount
        resulting[creditor] -= amount
    assert all(value == Decimal("0.00") for value in resulting.values())
    assert sum((transfer[2] for transfer in suggested), Decimal("0.00")) == Decimal("100.00")


def test_simplification_rejects_nonzero_residual():
    with pytest.raises(ValueError, match="net to zero"):
        simplify_debts({1: Decimal("1.00"), 2: Decimal("0.00")})
