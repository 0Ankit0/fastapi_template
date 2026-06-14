from __future__ import annotations

from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from src.db.session import get_session 

DB = Annotated[AsyncSession, Depends(get_session)]