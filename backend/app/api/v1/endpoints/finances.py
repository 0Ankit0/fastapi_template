from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from app.api import deps
from app.models.user import User
from app.models.finances import Product, Price, Subscription, Customer
from app.schemas.finances import ProductRead, PriceRead, CheckoutSessionCreate, CheckoutSessionResponse
from app.db.session import AsyncSession
from app.core.config import settings
import stripe

# Initialize Stripe
# stripe.api_key = settings.STRIPE_SECRET_KEY # Ensure this is in config

router = APIRouter()

@router.get("/products/", response_model=List[ProductRead])
async def read_products(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    # return await db.execute(select(Product).offset(skip).limit(limit)).scalars().all()
    # For now, stub response or return from DB
    result = await db.execute(select(Product).where(Product.active == True))
    return result.scalars().all()

@router.get("/prices/", response_model=List[PriceRead])
async def read_prices(
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    result = await db.execute(select(Price).where(Price.active == True))
    return result.scalars().all()

@router.post("/checkout-session/", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    checkout_in: CheckoutSessionCreate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Create a Stripe Checkout Session.
    """
    # 1. Get Tenant Customer
    # Find customer associated with user's current tenant context
    # Assuming user has a 'default' tenant or we pick one. 
    # For now, let's find the customer for the user's first tenant membership.
    
    # Note: In a real app, `current_user` should carry context about which tenant they are acting on.
    # We will assume `checkout_in` might carry tenant_id info in future, or we pick one.
    
    from app.models.tenant import TenantMembership
    membership_query = select(TenantMembership).where(TenantMembership.user_id == current_user.id)
    membership_result = await db.execute(membership_query)
    membership = membership_result.scalars().first()
    
    if not membership:
        raise HTTPException(status_code=400, detail="User belongs to no tenant")
        
    customer_query = select(Customer).where(Customer.tenant_id == membership.tenant_id)
    customer_result = await db.execute(customer_query)
    customer = customer_result.scalars().first()
    
    if not customer:
         raise HTTPException(status_code=400, detail="Tenant has no billing customer initialized")

    try:
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": checkout_in.price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=checkout_in.success_url,
            cancel_url=checkout_in.cancel_url,
            metadata={"tenant_id": str(membership.tenant_id)}
        )
        return {
            "session_id": session.id,
            "url": session.url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/portal-session/")
async def create_portal_session(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Create Stripe Billing Portal Session.
    """
    # Logic to find customer (DUPLICATED - move to service/dependency in refactor)
    from app.models.tenant import TenantMembership
    membership_result = await db.execute(select(TenantMembership).where(TenantMembership.user_id == current_user.id))
    membership = membership_result.scalars().first()
    
    if not membership:
        raise HTTPException(status_code=400, detail="User belongs to no tenant")
    
    customer_result = await db.execute(select(Customer).where(Customer.tenant_id == membership.tenant_id))
    customer = customer_result.scalars().first()
    
    if not customer:
        raise HTTPException(status_code=400, detail="No customer found")
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=settings.FRONTEND_URL
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subscriptions/", response_model=List[Any]) # Use schema
async def read_subscriptions(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tenant_id: int = None 
) -> Any:
    """
    Get subscriptions for a tenant.
    """
    target_tenant_id = tenant_id
    if not target_tenant_id:
         # Find default
         from app.models.tenant import TenantMembership
         res = await db.execute(select(TenantMembership).where(TenantMembership.user_id == current_user.id))
         m = res.scalars().first()
         if m:
             target_tenant_id = m.tenant_id
             
    if not target_tenant_id:
        return []

    # Get customer
    c_res = await db.execute(select(Customer).where(Customer.tenant_id == target_tenant_id))
    customer = c_res.scalars().first()
    
    if not customer:
        return []
        
    query = select(Subscription).where(Subscription.customer_id == customer.id)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/payment-methods/", response_model=List[Any])
async def read_payment_methods(
     db: AsyncSession = Depends(deps.get_db),
     current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get payment methods from Stripe.
    """
    # 1. Find Customer
    from app.models.tenant import TenantMembership
    res = await db.execute(select(TenantMembership).where(TenantMembership.user_id == current_user.id))
    m = res.scalars().first()
    if not m:
        return []
        
    c_res = await db.execute(select(Customer).where(Customer.tenant_id == m.tenant_id))
    customer = c_res.scalars().first()
    
    if not customer:
        return []

    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=customer.id,
            type="card",
        )
        return payment_methods.data
    except Exception:
        return []

# Webhook is now in webhooks.py, remove from here if duplicate

