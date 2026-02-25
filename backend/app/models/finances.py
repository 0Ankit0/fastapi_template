from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, BigInteger, JSON
from app.models.tenant import Tenant

class PriceType(str, Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"

class PriceInterval(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"

class ProductBase(SQLModel):
    id: str = Field(primary_key=True) # Stripe ID
    name: str
    active: bool = True
    description: Optional[str] = None
    meta_data: dict = Field(default={}, sa_column=Column(JSON))

class Product(ProductBase, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PriceBase(SQLModel):
    id: str = Field(primary_key=True) # Stripe ID
    product_id: str = Field(foreign_key="product.id")
    active: bool = True
    currency: str = "usd"
    unit_amount: Optional[int] = Field(sa_column=Column(BigInteger)) # In cents
    type: PriceType = PriceType.RECURRING
    interval: Optional[PriceInterval] = None

class Price(PriceBase, table=True):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class CustomerBase(SQLModel):
    id: str = Field(primary_key=True) # Stripe ID
    tenant_id: int = Field(foreign_key="tenant.id", unique=True)
    email: Optional[str] = None
    name: Optional[str] = None

class Customer(CustomerBase, table=True):
    tenant: "Tenant" = Relationship()

class SubscriptionBase(SQLModel):
    id: str = Field(primary_key=True) # Stripe ID
    customer_id: str = Field(foreign_key="customer.id")
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False

class Subscription(SubscriptionBase, table=True):
    # Relation to prices/items could be added but simplified for now
    created_at: datetime = Field(default_factory=datetime.utcnow)
