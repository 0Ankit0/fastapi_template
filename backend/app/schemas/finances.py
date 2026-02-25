from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel
from app.models.finances import ProductBase, PriceBase, SubscriptionBase

class ProductRead(ProductBase):
    pass

class PriceRead(PriceBase):
    pass

class SubscriptionRead(SubscriptionBase):
    pass

class CheckoutSessionCreate(SQLModel):
    price_id: str
    success_url: str
    cancel_url: str

class CheckoutSessionResponse(SQLModel):
    session_id: str
    url: str
