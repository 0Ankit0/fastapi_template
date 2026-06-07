from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db 

from apps.iam.dependencies import get_current_user 
from apps.iam.models import User

from apps.organizations.dependencies import get_current_org 
from apps.organizations.models import Organization

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentOrg = Annotated[Organization, Depends(get_current_org)]