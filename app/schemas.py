"""Request and response models (the API's public contract)."""
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.domain import OrderStatus

Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class RestaurantOut(BaseModel):
    id: int
    name: str
    cuisine: str
    opens_at: str
    closes_at: str
    avg_prep_minutes: int


class MenuItemOut(BaseModel):
    id: int
    restaurant_id: int
    name: str
    price_cents: int


class OrderItemIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    restaurant_id: int
    address: Address
    items: list[OrderItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
    menu_item_id: int
    name: str
    quantity: int
    unit_price_cents: int


class OrderOut(BaseModel):
    id: int
    restaurant_id: int
    status: OrderStatus
    total_cents: int
    address: str
    created_at: str
    items: list[OrderItemOut]


class StatusUpdate(BaseModel):
    status: OrderStatus
