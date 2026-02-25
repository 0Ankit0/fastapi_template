from datetime import datetime
from typing import Optional
import stripe
from sqlmodel import select
from app.core.config import settings
from app.db.session import AsyncSession
from app.models.finances import Price, Customer, Subscription
from app.models.tenant import Tenant

# Configure Stripe
stripe.api_key = settings.STRIPE_LIVE_SECRET_KEY if settings.STRIPE_LIVE_MODE else settings.STRIPE_TEST_SECRET_KEY

class SubscriptionService:
    @staticmethod
    async def initialize_tenant(db: AsyncSession, tenant: Tenant) -> None:
        """
        Initialize tenant with a Free tier subscription.
        """
        # 1. Get or Create Customer
        result = await db.execute(select(Customer).where(Customer.tenant_id == tenant.id))
        customer = result.scalars().first()
        
        if not customer:
            try:
                stripe_customer = stripe.Customer.create(
                    email=tenant.billing_email or tenant.name, # Use name as fallback or need creator email
                    name=tenant.name,
                    metadata={"tenant_id": str(tenant.id)}
                )
                customer = Customer(
                    id=stripe_customer.id,
                    tenant_id=tenant.id,
                    email=tenant.billing_email,
                    name=tenant.name
                )
                db.add(customer)
                await db.commit()
                await db.refresh(customer)
            except Exception as e:
                print(f"Error creating Stripe customer: {e}")
                return

        # 2. Subscribe to Free Plan (if defined)
        # We need a Free Price ID. 
        # In a real app we would have synced Prices and found the one with amount=0
        
        # Example logic:
        # free_price = await db.execute(select(Price).where(Price.unit_amount == 0, Price.active == True))
        # price_obj = free_price.scalars().first()
        
        # if price_obj:
        #     try:
        #         stripe.Subscription.create(
        #             customer=customer.id,
        #             items=[{"price": price_obj.id}],
        #             metadata={"tenant_id": str(tenant.id)}
        #         )
        #     except Exception:
        #         pass
        pass

    @staticmethod
    async def create_schedule(db: AsyncSession, tenant: Tenant, price_id: str):
        # Logic to create a subscription schedule (e.g. for upgrades/downgrades)
        pass
