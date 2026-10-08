from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PaymentResult:
    reference: str | None
    status: str
    instructions: str


class PaymentProvider(Protocol):
    def create_payment(self, amount: Decimal, currency: str, reference: str) -> PaymentResult: ...
    def get_payment_status(self, reference: str) -> PaymentResult: ...
    def cancel_payment(self, reference: str) -> PaymentResult: ...


class ManualPaymentProvider:
    def create_payment(self, amount: Decimal, currency: str, reference: str) -> PaymentResult:
        return PaymentResult(None, "MANUAL", "Transfer outside GroupPay; no money was moved by this app.")

    def get_payment_status(self, reference: str) -> PaymentResult:
        return PaymentResult(reference, "MANUAL", "Payment status is confirmed by group members.")

    def cancel_payment(self, reference: str) -> PaymentResult:
        return PaymentResult(reference, "CANCELLED", "No external payment was created.")
