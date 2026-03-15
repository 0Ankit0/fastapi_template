"""
Subscription API: plan management (superuser) + subscribe/renew/cancel (owner).
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from src.apps.iam.api.deps import get_db, get_current_user as get_current_active_user
from src.apps.iam.models.user import User
from src.apps.subscription.models.plan import SubscriptionPlan
from src.apps.subscription.models.subscription import OwnerSubscription, SubscriptionStatus
from src.apps.subscription.services.subscription_service import (
    get_subscription,
    start_trial,
    activate_subscription,
    cancel_subscription,
    is_subscription_active,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class PlanCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    price_monthly: float
    price_quarterly: Optional[float] = None
    price_yearly: Optional[float] = None
    # the original 'max_grounds' field is retained from the futsal template
    # but in a generic project it represents the maximum number of tenants
    max_grounds: int = 1
    max_staff: int = 2
    trial_days: int = 14
    features: Optional[str] = None
    is_public: bool = True


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_monthly: Optional[float] = None
    price_quarterly: Optional[float] = None
    price_yearly: Optional[float] = None
    max_grounds: Optional[int] = None
    max_staff: Optional[int] = None
    trial_days: Optional[int] = None
    features: Optional[str] = None
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    price_monthly: float
    price_quarterly: Optional[float]
    price_yearly: Optional[float]
    # note: 'max_grounds' effectively means max_tenants in a generic setup
    max_grounds: int
    max_staff: int
    trial_days: int
    features: Optional[str]
    is_active: bool
    is_public: bool


class SubscriptionStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: SubscriptionStatus
    plan: Optional[PlanResponse]
    current_period_end: Optional[str]
    trial_ends_at: Optional[str]
    cancel_at_period_end: bool
    billing_interval: str
    is_active: bool


class PaymentInitiateRequest(BaseModel):
    plan_id: int
    billing_interval: str = "monthly"  # monthly | quarterly | yearly
    provider: str = "khalti"           # khalti | esewa | stripe
    return_url: str                    # frontend callback URL


class PaymentVerifyRequest(BaseModel):
    plan_id: int
    transaction_id: int
    provider_token: str  # Khalti token or eSewa refId
    billing_interval: str = "monthly"  # monthly | quarterly | yearly


# ── Public: List Plans ─────────────────────────────────────────────────────────

@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Public endpoint — anyone can view available subscription plans."""
    result = await db.execute(
        select(SubscriptionPlan).where(
            SubscriptionPlan.is_active == True,
            SubscriptionPlan.is_public == True,
        )
    )
    return result.scalars().all()


@router.get("/plans/all", response_model=list[PlanResponse])
async def list_all_plans(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Superuser only: list all plans including inactive."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required.")
    result = await db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.id))
    return result.scalars().all()


# ── Superuser: Plan management ─────────────────────────────────────────────────

@router.post("/plans", response_model=PlanResponse, status_code=201)
async def create_plan(
    data: PlanCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Superuser only: create a new subscription plan."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required.")
    plan = SubscriptionPlan(**data.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: int,
    data: PlanUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Superuser only: update plan fields."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required.")
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    for key, val in data.model_dump(exclude_unset=True).items():
        if hasattr(plan, key) and key not in ("id", "created_at"):
            setattr(plan, key, val)
    plan.updated_at = datetime.utcnow()
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Superuser only: deactivate (soft-delete) a plan."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required.")
    plan = await db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    plan.is_active = False
    plan.updated_at = datetime.utcnow()
    db.add(plan)
    await db.commit()


# ── Superuser: view all subscriptions ────────────────────────────────────────

@router.get("/admin/all", tags=["admin"])
async def list_all_subscriptions(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required.")
    result = await db.execute(
        select(OwnerSubscription)
        .options(selectinload(OwnerSubscription.plan))
        .offset(skip)
        .limit(limit)
    )
    subs = result.scalars().all()
    return [
        {
            "owner_id": s.owner_id,
            "plan": s.plan,
            "status": s.status,
            "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            "created_at": s.created_at.isoformat(),
        }
        for s in subs
    ]


@router.patch("/admin/{owner_id}/activate", tags=["admin"])
async def manually_activate_subscription(
    owner_id: int,
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Superuser: manually activate subscription (e.g., after manual bank transfer)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required.")
    sub = await activate_subscription(db, owner_id, plan_id, transaction_id=0)
    return sub


# ── Owner: get subscription status ────────────────────────────────────────────

@router.get("/me", response_model=SubscriptionStatusResponse)
async def my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_subscription(db, current_user.id)
    plan = await db.get(SubscriptionPlan, sub.plan_id) if sub else None
    return SubscriptionStatusResponse(
        status=sub.status if sub else SubscriptionStatus.EXPIRED,
        plan=plan,
        current_period_end=sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        trial_ends_at=sub.trial_ends_at.isoformat() if sub and sub.trial_ends_at else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
        billing_interval=sub.billing_interval if sub else "monthly",
        is_active=is_subscription_active(sub),
    )


# ── Owner: start trial ─────────────────────────────────────────────────────────

@router.post("/trial/{plan_id}", status_code=201)
async def start_trial_subscription(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a free trial for the owner. Only once; raises 409 if already subscribed."""
    existing = await get_subscription(db, current_user.id)
    if existing:
        raise HTTPException(status_code=409, detail="You already have a subscription record.")
    sub = await start_trial(db, current_user.id, plan_id)
    return sub


# ── Owner: initiate subscription payment ──────────────────────────────────────

@router.post("/initiate-payment")
async def initiate_subscription_payment(
    req: PaymentInitiateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a payment for a subscription plan.
    Returns the provider's payment_url to redirect the user to.
    """
    import uuid
    from src.apps.finance.models.payment import PaymentProvider
    from src.apps.finance.schemas.payment import InitiatePaymentRequest as ProviderInitRequest
    from src.apps.finance.api.v1.payment import _get_provider

    # Resolve plan and price
    plan = await db.get(SubscriptionPlan, req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    interval = req.billing_interval.lower()
    if interval == "quarterly":
        price_npr = plan.price_quarterly or plan.price_monthly * 3
    elif interval == "yearly":
        price_npr = plan.price_yearly or plan.price_monthly * 12
    else:
        price_npr = plan.price_monthly

    # Convert NPR → paisa (Khalti/eSewa require smallest unit)
    amount_paisa = int(price_npr * 100)

    # Build a unique order reference
    order_id = f"SUB-{current_user.id}-{plan.id}-{uuid.uuid4().hex[:8].upper()}"
    order_name = f"{plan.name} ({interval.capitalize()})"

    try:
        provider_enum = PaymentProvider(req.provider.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {req.provider}")

    try:
        provider_svc = _get_provider(provider_enum)
    except HTTPException:
        raise HTTPException(status_code=400, detail=f"Payment provider '{req.provider}' is not enabled.")

    provider_req = ProviderInitRequest(
        provider=provider_enum,
        amount=amount_paisa,
        purchase_order_id=order_id,
        purchase_order_name=order_name,
        return_url=req.return_url,
        website_url="",
        customer_name=current_user.username,
        customer_email=current_user.email,
    )

    try:
        result = await provider_svc.initiate_payment(provider_req, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Payment provider error: {exc}")

    return result


# ── Owner: verify payment and activate ────────────────────────────────────────

@router.post("/verify-payment")
async def verify_payment_and_activate(
    req: PaymentVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the frontend after Khalti/eSewa redirects back with a token.
    Looks up the PaymentTransaction, confirms it's completed, then activates subscription.
    """
    from src.apps.finance.models.payment import PaymentTransaction, PaymentStatus

    tx = await db.get(PaymentTransaction, req.transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Payment transaction not found.")
    if tx.status != PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=402,
            detail="Payment has not been completed. Please complete the payment first.",
        )

    # Detect downgrade: compare old plan limits vs new plan limits
    old_sub = await get_subscription(db, current_user.id)
    old_plan = await db.get(SubscriptionPlan, old_sub.plan_id) if old_sub else None
    new_plan = await db.get(SubscriptionPlan, req.plan_id)
    is_downgrade = bool(
        old_plan and new_plan and (
            new_plan.max_grounds < old_plan.max_grounds or
            new_plan.max_staff < old_plan.max_staff
        )
    )

    sub = await activate_subscription(db, current_user.id, req.plan_id, req.transaction_id, req.billing_interval)
    return {
        "message": "Subscription activated.",
        "subscription": sub,
        "needs_limit_adjustment": is_downgrade,
        "new_max_grounds": new_plan.max_grounds if new_plan else None,
        "new_max_staff": new_plan.max_staff if new_plan else None,
    }


# ── Owner: cancel subscription ─────────────────────────────────────────────────

@router.post("/cancel")
async def cancel_my_subscription(
    immediately: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await cancel_subscription(db, current_user.id, immediately=immediately)
    msg = "Subscription cancelled immediately." if immediately else "Subscription will cancel at end of current period."
    return {"message": msg, "subscription": sub}


# ── Owner: subscription usage vs plan limits ──────────────────────────────────

class TenantUsageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None
    is_active: bool
    disabled_by_limit: bool

class MemberUsageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    invite_email: str
    role: str
    is_active: bool
    disabled_by_limit: bool

class SubscriptionUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    max_tenants: int
    max_staff: int
    active_tenants: int
    active_staff: int
    tenants: list[TenantUsageItem]  # tenant list for usage
    members: list[MemberUsageItem]
    exceeds_tenants: bool
    exceeds_staff: bool


@router.get("/usage", response_model=SubscriptionUsageResponse)
async def get_subscription_usage(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Owner: current resource usage vs plan limits."""
    from src.apps.multitenancy.models.tenant import Tenant, TenantMember
    from sqlmodel import select as sel

    sub = await get_subscription(db, current_user.id)
    plan = await db.get(SubscriptionPlan, sub.plan_id) if sub else None
    max_tenants = plan.max_grounds if plan else 1
    max_staff = plan.max_staff if plan else 0

    tenants_result = await db.execute(
        sel(Tenant).where(Tenant.owner_id == current_user.id)
        .order_by(Tenant.created_at)
    )
    all_tenants = tenants_result.scalars().all()

    staff_result = await db.execute(
        sel(TenantMember).join(
            Tenant, TenantMember.tenant_id == Tenant.id
        ).where(Tenant.owner_id == current_user.id)
    )
    all_staff = staff_result.scalars().all()

    active_tenants = sum(1 for g in all_tenants if g.is_active)
    active_staff = sum(1 for s in all_staff if s.is_active)

    return SubscriptionUsageResponse(
        max_tenants=max_tenants,
        max_staff=max_staff,
        active_tenants=active_tenants,
        active_staff=active_staff,
        tenants=[
            TenantUsageItem(
                id=g.id,
                name=g.name,
                description=getattr(g, "description", None),
                is_active=g.is_active,
                disabled_by_limit=g.disabled_by_limit,
            )
            for g in all_tenants
        ],
        members=[
            MemberUsageItem(
                id=s.id, tenant_id=s.tenant_id, invite_email=s.invite_email,
                role=s.role, is_active=s.is_active, disabled_by_limit=s.disabled_by_limit,
            )
            for s in all_staff
        ],
        exceeds_tenants=active_tenants > max_tenants,
        exceeds_staff=active_staff > max_staff,
    )


class LimitAdjustmentRequest(BaseModel):
    tenants_to_disable: list[int] = []   # tenant IDs to disable
    members_to_disable: list[int] = []   # member IDs to disable


@router.post("/apply-limit-adjustment", status_code=200)
async def apply_limit_adjustment(
    req: LimitAdjustmentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Owner: after a downgrade, select which tenants/members to disable.
    Disables selected items and marks them as disabled_by_limit.
    """
    from src.apps.multitenancy.models.tenant import Tenant, TenantMember
    from datetime import datetime

    disabled_tenants, disabled_members = [], []

    for tid in req.tenants_to_disable:
        tenant = await db.get(Tenant, tid)
        if tenant and tenant.owner_id == current_user.id:
            tenant.is_active = False
            tenant.disabled_by_limit = True
            tenant.updated_at = datetime.utcnow()
            db.add(tenant)
            disabled_tenants.append(tid)

    for mid in req.members_to_disable:
        member = await db.get(TenantMember, mid)
        if member:
            # verify the tenant belongs to this owner
            tenant = await db.get(Tenant, member.tenant_id)
            if tenant and tenant.owner_id == current_user.id:
                member.is_active = False
                member.disabled_by_limit = True
                db.add(member)
                disabled_members.append(mid)

    await db.commit()
    return {
        "message": "Limit adjustment applied.",
        "disabled_tenants": disabled_tenants,
        "disabled_members": disabled_members,
    }
