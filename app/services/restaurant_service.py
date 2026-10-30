from app.errors import NotFoundError
from app.repositories.restaurant_repository import RestaurantRepository


class RestaurantService:
    def __init__(self, restaurants: RestaurantRepository):
        self.restaurants = restaurants

    def list_restaurants(self) -> list[dict]:
        return self.restaurants.list_all()

    def get_menu(self, restaurant_id: int) -> list[dict]:
        if self.restaurants.get(restaurant_id) is None:
            raise NotFoundError(f"Restaurant {restaurant_id} not found")
        return self.restaurants.list_menu(restaurant_id)
