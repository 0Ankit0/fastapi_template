import strawberry
from typing import Optional, List
from strawberry.scalars import JSON

from src.apps.finance.models.payment import PaymentProvider, PaymentStatus
from src.apps.finance.schemas.payment import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
    PaymentTransactionRead,
)


@strawberry.input
class InitiatePaymentRequestType:
    """GraphQL input for initiating a payment."""
    provider: PaymentProvider
    amount: int
    purchase_order_id: str
    purchase_order_name: str
    return_url: str
    website_url: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


@strawberry.type
class InitiatePaymentResponseType:
    """GraphQL response after initiating a payment."""
    transaction_id: int
    provider: PaymentProvider
    status: PaymentStatus
    payment_url: Optional[str] = None
    provider_pidx: Optional[str] = None
    extra: Optional[JSON] = None


@strawberry.input
class VerifyPaymentRequestType:
    """GraphQL input for verifying a payment."""
    provider: PaymentProvider
    pidx: Optional[str] = None
    oid: Optional[str] = None
    refId: Optional[str] = None
    data: Optional[str] = None
    transaction_id: Optional[int] = None


@strawberry.type
class VerifyPaymentResponseType:
    """GraphQL response after verifying a payment."""
    transaction_id: int
    provider: PaymentProvider
    status: PaymentStatus
    amount: Optional[int] = None
    provider_transaction_id: Optional[str] = None
    extra: Optional[JSON] = None


@strawberry.type
class PaymentTransactionType:
    """GraphQL type for stored payment transactions."""
    id: int
    provider: PaymentProvider
    status: PaymentStatus
    amount: int
    currency: str
    purchase_order_id: str
    purchase_order_name: str
    provider_transaction_id: Optional[str]
    provider_pidx: Optional[str]
    return_url: str
    website_url: str
    failure_reason: Optional[str]


@strawberry.type
class Providers:
    providers: List[str]
