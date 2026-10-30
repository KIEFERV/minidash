"""FastAPI dependency wiring: connection -> repositories -> services."""
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request

from app.database import connect
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.order_service import OrderService
from app.services.restaurant_service import RestaurantService


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """One SQLite connection per request, always closed afterwards."""
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_now(request: Request) -> datetime:
    """Current time from the app's injected clock (see create_app)."""
    return request.app.state.clock()


DbDep = Annotated[sqlite3.Connection, Depends(get_db)]
NowDep = Annotated[datetime, Depends(get_now)]


def get_restaurant_service(conn: DbDep) -> RestaurantService:
    return RestaurantService(RestaurantRepository(conn))


def get_order_service(conn: DbDep, now: NowDep) -> OrderService:
    return OrderService(OrderRepository(conn), RestaurantRepository(conn), now)


RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
