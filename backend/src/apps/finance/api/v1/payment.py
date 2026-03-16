"""
Finance payment API endpoints (v1).

POST /payments/initiate     — initiate a payment with any provider
POST /payments/verify       — verify / process a provider callback
GET  /payments/{id}         — retrieve a stored transaction record
GET  /payments/             — list transactions (authenticated users)
"""
from typing import Optional, List

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from src.apps.core.config import settings

from src.apps.finance.models.payment import PaymentProvider, PaymentTransaction
from src.apps.finance.schemas.payment import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    PaymentTransactionRead,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from src.apps.finance.schemas.graphql_payment import (
    InitiatePaymentRequestType,
    InitiatePaymentResponseType,
    VerifyPaymentRequestType,
    VerifyPaymentResponseType,
    PaymentTransactionType,
    Providers,
)
from src.apps.finance.services.base import BasePaymentProvider
from src.apps.finance.services.esewa import EsewaService
from src.apps.finance.services.khalti import KhaltiService
from src.apps.finance.services.stripe import StripeService
from src.apps.finance.services.paypal import PayPalService
from src.apps.iam.api.deps import get_db, get_current_user
from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import PaymentEvents

router = APIRouter()


async def get_graphql_context(
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
):
    return {"db": db, "analytics": analytics}

# ---------------------------------------------------------------------------
# Provider registry — built at startup, respects per-provider enabled flags
# ---------------------------------------------------------------------------

def _build_registry() -> dict[PaymentProvider, BasePaymentProvider]:
    registry: dict[PaymentProvider, BasePaymentProvider] = {}
    if settings.KHALTI_ENABLED:
        registry[PaymentProvider.KHALTI] = KhaltiService()
    if settings.ESEWA_ENABLED:
        registry[PaymentProvider.ESEWA] = EsewaService()
    if settings.STRIPE_ENABLED:
        registry[PaymentProvider.STRIPE] = StripeService()
    if settings.PAYPAL_ENABLED:
        registry[PaymentProvider.PAYPAL] = PayPalService()
    return registry

_PROVIDERS: dict[PaymentProvider, BasePaymentProvider] = _build_registry()


def _get_provider(provider: PaymentProvider) -> BasePaymentProvider:
    svc = _PROVIDERS.get(provider)
    if svc is None:
        # Distinguish "disabled" from "unknown"
        known = {p.value for p in PaymentProvider}
        if provider.value in known:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Payment provider '{provider}' is currently disabled.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment provider '{provider}' is not supported.",
        )
    return svc


# ---------------------------------------------------------------------------
# GraphQL payment API
# ---------------------------------------------------------------------------

@strawberry.type
class Query:
    @strawberry.field
    async def providers(self, info: Info) -> Providers:
        """Return the list of currently enabled payment providers."""
        return Providers(providers=[p.value for p in _PROVIDERS])

    @strawberry.field
    async def transaction(self, info: Info, transaction_id: int) -> PaymentTransactionType | None:
        """Fetch a stored payment transaction by its internal ID."""
        tx = await info.context["db"].get(PaymentTransaction, transaction_id)
        if tx is None:
            return None
        return PaymentTransactionType.from_pydantic(PaymentTransactionRead.model_validate(tx))

    @strawberry.field
    async def transactions(
        self,
        info: Info,
        provider: Optional[PaymentProvider] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PaymentTransactionType]:
        """List payment transactions with optional provider filter."""
        db: AsyncSession = info.context["db"]
        query = select(PaymentTransaction).order_by(col(PaymentTransaction.id).desc()).limit(limit).offset(offset)

        if provider:
            query = query.where(PaymentTransaction.provider == provider)

        result = await db.execute(query)
        transactions = result.scalars().all()
        return [
            PaymentTransactionType.from_pydantic(PaymentTransactionRead.model_validate(tx))
            for tx in transactions
        ]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def initiate_payment(self, info: Info, input: InitiatePaymentRequestType) -> InitiatePaymentResponseType:
        """Initiate a new payment with the specified provider."""
        db: AsyncSession = info.context["db"]
        analytics: AnalyticsService = info.context["analytics"]

        provider_svc = _get_provider(input.provider)
        request_model = InitiatePaymentRequest.model_validate(input.__dict__)
        try:
            result = await provider_svc.initiate_payment(request_model, db)
            distinct_id = str(result.transaction_id)
            await analytics.capture(
                distinct_id,
                PaymentEvents.PAYMENT_INITIATED,
                {
                    "provider": input.provider.value,
                    "amount": input.amount,
                    "purchase_order_id": input.purchase_order_id,
                    "transaction_id": result.transaction_id,
                },
            )
            return InitiatePaymentResponseType.from_pydantic(result)
        except ValueError as exc:
            raise GraphQLError(str(exc))
        except Exception as exc:
            raise GraphQLError(f"Payment provider error: {exc}")

    @strawberry.mutation
    async def verify_payment(self, info: Info, input: VerifyPaymentRequestType) -> VerifyPaymentResponseType:
        """Verify a payment after the provider redirects the user back."""
        db: AsyncSession = info.context["db"]
        analytics: AnalyticsService = info.context["analytics"]

        provider_svc = _get_provider(input.provider)
        request_model = VerifyPaymentRequest.model_validate(input.__dict__)
        try:
            result = await provider_svc.verify_payment(request_model, db)
            from src.apps.finance.models.payment import PaymentStatus
            event = (
                PaymentEvents.PAYMENT_COMPLETED
                if result.status == PaymentStatus.COMPLETED
                else PaymentEvents.PAYMENT_FAILED
            )
            await analytics.capture(
                str(result.transaction_id),
                event,
                {
                    "provider": input.provider.value,
                    "status": result.status.value,
                    "amount": result.amount,
                    "transaction_id": result.transaction_id,
                },
            )
            return VerifyPaymentResponseType.from_pydantic(result)
        except ValueError as exc:
            raise GraphQLError(str(exc))
        except Exception as exc:
            raise GraphQLError(f"Payment provider error: {exc}")


schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_router = GraphQLRouter(schema, context_getter=get_graphql_context)
