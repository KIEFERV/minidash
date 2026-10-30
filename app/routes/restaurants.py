from fastapi import APIRouter

from app.dependencies import RestaurantServiceDep
from app.schemas import MenuItemOut, RestaurantOut

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("", response_model=list[RestaurantOut])
def list_restaurants(service: RestaurantServiceDep):
    return service.list_restaurants()


@router.get("/{restaurant_id}/menu", response_model=list[MenuItemOut])
def get_menu(restaurant_id: int, service: RestaurantServiceDep):
    return service.get_menu(restaurant_id)
