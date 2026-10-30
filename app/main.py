import asyncio
import os
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import connect, init_db
from app.errors import MiniDashError
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.routes import orders, restaurants
from app.scheduler import release_loop
from app.services.order_service import OrderService


def create_app(
    db_path: str | None = None,
    clock: Callable[[], datetime] | None = None,
    release_interval: float | None = 30.0,
) -> FastAPI:
    """Application factory.

    db_path           defaults to $MINIDASH_DB or ./minidash.db
    clock             returns the current (naive, server-local) time; defaults to
                      datetime.now. All time-dependent logic goes through it.
    release_interval  seconds between background runs that release due
                      scheduled orders; None disables the background job.
    """
    path = db_path or os.environ.get("MINIDASH_DB", "minidash.db")
    now = clock or datetime.now

    def release_once() -> list[int]:
        conn = connect(path)
        try:
            service = OrderService(OrderRepository(conn), RestaurantRepository(conn), now())
            return service.release_due_orders()
        finally:
            conn.close()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db(path)  # create/migrate tables and seed on first start
        task = None
        if release_interval:
            task = asyncio.create_task(release_loop(release_once, release_interval))
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(
        title="MiniDash",
        description="A small food-delivery API.",
        version="1.1.0",
        lifespan=lifespan,
    )
    app.state.db_path = path
    app.state.clock = now

    @app.exception_handler(MiniDashError)
    async def handle_domain_error(_: Request, exc: MiniDashError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(restaurants.router)
    app.include_router(orders.router)
    return app


app = create_app()
