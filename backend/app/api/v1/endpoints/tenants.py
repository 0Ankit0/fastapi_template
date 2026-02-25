from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from app.api import deps
from app.models.user import User
from app.models.tenant import Tenant, TenantMembership
from app.schemas.tenant import TenantRead, TenantCreate
from app.db.session import AsyncSession
from app.core.config import settings

router = APIRouter()

@router.get("/", response_model=Any)
async def read_tenants(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve tenants.
    """
    # Simply return tenants where user is a member
    result = await db.execute(
        select(Tenant).join(TenantMembership).where(TenantMembership.user_id == current_user.id)
    )
    tenants = result.scalars().all()
    
    # Return in DRF pagination format for frontend compatibility
    return {
        "results": tenants,
        "count": len(tenants),
        "next": None,
        "previous": None
    }

@router.post("/", response_model=TenantRead)
async def create_tenant(
    *,
    db: AsyncSession = Depends(deps.get_db),
    tenant_in: TenantCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new tenant.
    """
    slug = tenant_in.slug
    if not slug:
        slug = tenant_in.name.lower().replace(" ", "-")
        
    tenant = Tenant(
        name=tenant_in.name,
        slug=slug,
        type=tenant_in.type,
        creator_id=current_user.id
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    # Add membership
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=current_user.id,
        role="OWNER",
        is_accepted=True,
        invitation_accepted_at=datetime.utcnow()
    )
    db.add(membership)
    await db.commit()
    
    # Initialize Billing/Subscriptions
    from app.services.subscriptions import SubscriptionService
    await SubscriptionService.initialize_tenant(db, tenant)
    
    return tenant

@router.post("/{tenant_id}/invite/", response_model=Any)
async def invite_member(
    tenant_id: int,
    email: str,
    role: str = "MEMBER",
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    # Verify permission (User must be OWNER or ADMIN of tenant)
    # For now simply check if user is a member
    # In real app, check role
    
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # Check if already a member or invited
    # Logic to check existing membership...
    
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=None, # Not associated yet
        invitee_email_address=email,
        role=role,
        is_accepted=False
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    
    # Send Email
    from app.services.email import EmailService
    invite_url = f"{settings.FRONTEND_URL}/accept-invitation?token={membership.id}" # using ID as token for now
    await EmailService.send_email(
        subject=f"You're invited to join {tenant.name}",
        recipients=[email],
        template_name="tenant_invitation",
        context={
            "tenant_name": tenant.name,
            "invited_by": current_user.email,
            "invite_url": invite_url,
            "role": role
        }
    )
    
    return {"message": "Invitation sent"}

@router.get("/{tenant_id}/memberships/", response_model=Any)
async def read_tenant_memberships(
    tenant_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    # Verify access
    # Logic to check ...
    
    result = await db.execute(select(TenantMembership).where(TenantMembership.tenant_id == tenant_id))
    memberships = result.scalars().all()
    
    return {
        "results": memberships,
        "count": len(memberships),
        "next": None,
        "previous": None
    }

@router.patch("/{tenant_id}/", response_model=TenantRead)
async def update_tenant(
    tenant_id: int,
    tenant_in: dict, # Should use Schema
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    # Check permissions (OWNER)
    # ...
    
    for k, v in tenant_in.items():
        if hasattr(tenant, k) and v is not None:
             setattr(tenant, k, v)
             
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant
