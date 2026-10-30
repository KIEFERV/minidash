import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import init_db
from app.errors import MiniDashError
from app.routes import orders, restaurants


def create_app(db_path: str | None = None) -> FastAPI:
    """Application factory. ``db_path`` defaults to $MINIDASH_DB or ./minidash.db."""
    path = db_path or os.environ.get("MINIDASH_DB", "minidash.db")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db(path)  # create tables and seed on first start
        yield

    app = FastAPI(
        title="MiniDash",
        description="A small food-delivery API.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.db_path = path

    @app.exception_handler(MiniDashError)
    async def handle_domain_error(_: Request, exc: MiniDashError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(restaurants.router)
    app.include_router(orders.router)
    return app


app = create_app()
