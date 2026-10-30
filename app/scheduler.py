"""Background loop that releases due scheduled orders."""
import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger("minidash.scheduler")


async def release_loop(
    release_once: Callable[[], list[int]],
    interval: float,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Call ``release_once`` every ``interval`` seconds until cancelled.

    ``release_once`` does blocking SQLite work, so it runs in a worker thread.
    A failed run is logged and retried on the next tick. ``sleep`` is
    injectable so tests can drive the loop without real waiting.
    """
    while True:
        try:
            released = await asyncio.to_thread(release_once)
            if released:
                logger.info("Released scheduled orders: %s", released)
        except Exception:
            logger.exception("Releasing scheduled orders failed")
        await sleep(interval)
