from __future__ import annotations

from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status

from db.session import get_session 

from apps.iam.dependencies import get_current_user 
from apps.iam.models import User

from apps.organizations.dependencies import get_current_org 
from apps.organizations.models import Organization

DB = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentOrg = Annotated[Organization, Depends(get_current_org)]