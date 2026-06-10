from __future__ import annotations

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

class CreatedAtMixin:
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )

class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )