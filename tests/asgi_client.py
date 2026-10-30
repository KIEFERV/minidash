"""A tiny ASGI test client built on the standard library.

FastAPI's TestClient needs ``httpx``, which is outside the allowed dependency
list (fastapi, uvicorn, pytest). This client drives the real app through the
ASGI interface instead, including its startup/shutdown lifespan.
"""
import asyncio
import json
from dataclasses import dataclass


@dataclass
class Response:
    status_code: int
    headers: dict[str, str]
    content: bytes

    def json(self):
        return json.loads(self.content)

    @property
    def text(self) -> str:
        return self.content.decode()


class ASGIClient:
    def __init__(self, app):
        self.app = app
        self._loop = asyncio.new_event_loop()

    # -- lifecycle -----------------------------------------------------
    def __enter__(self):
        self._loop.run_until_complete(self._startup())
        return self

    def __exit__(self, *exc_info):
        try:
            self._loop.run_until_complete(self._shutdown())
        finally:
            self._loop.run_until_complete(self._loop.shutdown_default_executor())
            self._loop.close()

    async def _startup(self):
        self._to_app: asyncio.Queue = asyncio.Queue()
        self._from_app: asyncio.Queue = asyncio.Queue()
        scope = {"type": "lifespan", "asgi": {"version": "3.0"}, "state": {}}
        self._lifespan_task = asyncio.ensure_future(
            self.app(scope, self._to_app.get, self._from_app.put)
        )
        await self._to_app.put({"type": "lifespan.startup"})
        message = await self._from_app.get()
        assert message["type"] == "lifespan.startup.complete", message

    async def _shutdown(self):
        await self._to_app.put({"type": "lifespan.shutdown"})
        message = await self._from_app.get()
        assert message["type"] == "lifespan.shutdown.complete", message
        await self._lifespan_task

    # -- requests ------------------------------------------------------
    def get(self, path: str) -> Response:
        return self.request("GET", path)

    def post(self, path: str, json=None) -> Response:  # noqa: A002
        return self.request("POST", path, json)

    def patch(self, path: str, json=None) -> Response:  # noqa: A002
        return self.request("PATCH", path, json)

    def request(self, method: str, path: str, json_body=None) -> Response:
        return self._loop.run_until_complete(self._request(method, path, json_body))

    async def _request(self, method: str, path: str, json_body) -> Response:
        body = b""
        headers = [(b"host", b"testserver")]
        if json_body is not None:
            body = json.dumps(json_body).encode()
            headers += [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ]
        path_only, _, query = path.partition("?")
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path_only,
            "raw_path": path_only.encode(),
            "query_string": query.encode(),
            "root_path": "",
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "state": {},
        }

        request_sent = False

        async def receive():
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        status = 500
        response_headers: dict[str, str] = {}
        chunks: list[bytes] = []

        async def send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                response_headers.update(
                    {k.decode().lower(): v.decode() for k, v in message["headers"]}
                )
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        await self.app(scope, receive, send)
        return Response(status, response_headers, b"".join(chunks))
