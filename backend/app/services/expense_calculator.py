from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Sequence

from app.models.expense import SplitType

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class SplitValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SplitInput:
    user_id: int
    amount: Decimal | None = None
    percentage: Decimal | None = None
    shares: Decimal | None = None


@dataclass(frozen=True)
class SplitAllocation:
    user_id: int
    amount_owed: Decimal
    percentage: Decimal | None = None
    shares: Decimal | None = None


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def validate_total(total: Decimal) -> Decimal:
    if not total.is_finite() or total <= 0:
        raise SplitValidationError("Expense amount must be greater than zero")
    normalized = money(total)
    if normalized != total:
        raise SplitValidationError("Expense amount can have at most two decimal places")
    return normalized


def _cents(value: Decimal) -> int:
    return int((value / CENT).to_integral_exact())


def _allocate_proportionally(
    total: Decimal, weights: Sequence[tuple[int, Decimal]]
) -> dict[int, Decimal]:
    """Largest-remainder apportionment. Ties resolve by user id for stable output."""
    target_cents = _cents(total)
    weight_total = sum((weight for _, weight in weights), Decimal(0))
    if weight_total <= 0:
        raise SplitValidationError("Split values must add up to more than zero")
    floors: dict[int, int] = {}
    remainders: list[tuple[Decimal, int]] = []
    for user_id, weight in weights:
        raw_cents = Decimal(target_cents) * weight / weight_total
        floor_cents = int(raw_cents.to_integral_value(rounding=ROUND_DOWN))
        floors[user_id] = floor_cents
        remainders.append((raw_cents - floor_cents, user_id))
    cents_left = target_cents - sum(floors.values())
    for _, user_id in sorted(remainders, key=lambda item: (-item[0], item[1]))[:cents_left]:
        floors[user_id] += 1
    return {user_id: (Decimal(cents) * CENT).quantize(CENT) for user_id, cents in floors.items()}


def calculate_split(
    total: Decimal, split_type: SplitType, entries: Sequence[SplitInput]
) -> list[SplitAllocation]:
    total = validate_total(total)
    if not entries:
        raise SplitValidationError("At least one participant is required")
    ids = [entry.user_id for entry in entries]
    if len(set(ids)) != len(ids):
        raise SplitValidationError("Participants cannot be duplicated")
    ordered = sorted(entries, key=lambda entry: entry.user_id)

    if split_type == SplitType.EQUAL:
        if any(
            entry.amount is not None or entry.percentage is not None or entry.shares is not None
            for entry in ordered
        ):
            raise SplitValidationError(
                "Equal split participants must not include individual split values"
            )
        amounts = _allocate_proportionally(
            total, [(entry.user_id, Decimal(1)) for entry in ordered]
        )
        results = [SplitAllocation(entry.user_id, amounts[entry.user_id]) for entry in ordered]
    elif split_type == SplitType.EXACT:
        if any(entry.percentage is not None or entry.shares is not None for entry in ordered):
            raise SplitValidationError("Exact split accepts only amount values")
        if any(
            entry.amount is None or not entry.amount.is_finite() or entry.amount < 0
            for entry in ordered
        ):
            raise SplitValidationError("Each exact split amount must be zero or greater")
        if any(money(entry.amount) != entry.amount for entry in ordered):
            raise SplitValidationError("Exact split amounts can have at most two decimal places")
        if sum((entry.amount for entry in ordered), Decimal(0)) != total:
            raise SplitValidationError("Exact split amounts must total the expense amount")
        results = [SplitAllocation(entry.user_id, money(entry.amount)) for entry in ordered]
    elif split_type == SplitType.PERCENTAGE:
        if any(entry.amount is not None or entry.shares is not None for entry in ordered):
            raise SplitValidationError("Percentage split accepts only percentage values")
        if any(
            entry.percentage is None or not entry.percentage.is_finite() or entry.percentage <= 0
            for entry in ordered
        ):
            raise SplitValidationError("Each participant must have a positive percentage")
        if sum((entry.percentage for entry in ordered), Decimal(0)) != Decimal(100):
            raise SplitValidationError("Percentages must total 100")
        amounts = _allocate_proportionally(
            total, [(entry.user_id, entry.percentage) for entry in ordered]
        )
        results = [
            SplitAllocation(entry.user_id, amounts[entry.user_id], percentage=entry.percentage)
            for entry in ordered
        ]
    elif split_type == SplitType.SHARES:
        if any(entry.amount is not None or entry.percentage is not None for entry in ordered):
            raise SplitValidationError("Shares split accepts only share values")
        if any(
            entry.shares is None or not entry.shares.is_finite() or entry.shares <= 0
            for entry in ordered
        ):
            raise SplitValidationError("Each participant must have a positive number of shares")
        amounts = _allocate_proportionally(
            total, [(entry.user_id, entry.shares) for entry in ordered]
        )
        results = [
            SplitAllocation(entry.user_id, amounts[entry.user_id], shares=entry.shares)
            for entry in ordered
        ]
    else:
        raise SplitValidationError("Unsupported split type")

    if sum((result.amount_owed for result in results), ZERO) != total:
        raise SplitValidationError("Split allocation did not balance to the expense total")
    return results
