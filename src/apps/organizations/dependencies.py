

from typing_extensions import Annotated

from fastapi import Depends, Path, Query, Request

from src.apps.iam.dependencies import get_current_user
from src.apps.iam.models.user import User
from src.core.dependencies import DB
from src.apps.organizations.models import Organization
from src.db.query import select
from src.core.exceptions import NotFoundError

CurrentUser = Annotated[User, Depends(get_current_user)]
async def get_current_org(
    db: DB,
    current_user: CurrentUser,
    org: Annotated[str, Path(description="Organization slug")],
) -> Organization | None:
    """
    Get the current organization based on the org slug query parameter and user membership
    """
    try:
        if not org:
            raise NotFoundError("Organization slug is required")

        if current_user.is_superuser:
            result = await db.execute(
                select(Organization).where(Organization.slug == org)
            )
            organization = result.scalars().first()
            if not organization:
                raise NotFoundError("Organization not found")
            return organization
        
        # Check if the user is a member of the specified organization
        result = await db.execute(
            select(Organization).where(
                Organization.slug == org,
                Organization.members.any(id=current_user.id)
            )
        )
        organization = result.scalars().first()
        
        if not organization:
            raise NotFoundError("Organization not found or access denied")
        
        return organization
    except Exception:
        raise 
    