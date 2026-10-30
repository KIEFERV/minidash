from fastapi import APIRouter

from app.dependencies import OrderServiceDep
from app.schemas import OrderCreate, OrderOut, StatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, service: OrderServiceDep):
    return service.create_order(
        restaurant_id=payload.restaurant_id,
        address=payload.address,
        items=[(i.menu_item_id, i.quantity) for i in payload.items],
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, service: OrderServiceDep):
    return service.get_order(order_id)


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, payload: StatusUpdate, service: OrderServiceDep):
    return service.update_status(order_id, payload.status)
