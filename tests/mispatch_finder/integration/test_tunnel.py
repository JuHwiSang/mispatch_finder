import threading
import time
import queue
import secrets

import pytest
import requests
from fastapi import FastAPI, Request
from fastapi.responses import Response
import uvicorn

from mispatch_finder.infra.mcp.tunnel import Tunnel


@pytest.mark.integration
def test_tunnel_forwards_body_and_header() -> None:
    received: "queue.Queue[tuple[str, bytes]]" = queue.Queue()

    app = FastAPI()

    @app.post("/")
    async def root(req: Request) -> Response:  # type: ignore[override]
        body = await req.body()
        token = req.headers.get("x-test-token", "")
        received.put((token, body))
        return Response(content=body, media_type="text/plain")

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # Wait for server to start
    for _ in range(500):  # ~5s max
        if getattr(server, "started", False) and getattr(server, "servers", None):
            break
        time.sleep(0.01)

    assert getattr(server, "servers", None), "uvicorn did not start"
    sock = server.servers[0].sockets[0]
    local_port = sock.getsockname()[1]
    public_url, tunnel = Tunnel.start_tunnel("127.0.0.1", local_port)

    payload = secrets.token_urlsafe(16)
    header_val = secrets.token_urlsafe(8)

    resp = requests.post(
        public_url,
        data=payload.encode("utf-8"),
        headers={"X-Test-Token": header_val, "Content-Type": "text/plain"},
        timeout=30,
    )
    resp.raise_for_status()
    echoed = resp.text

    token_seen, body_seen = received.get(timeout=30)
    assert token_seen == header_val
    assert body_seen.decode("utf-8") == payload
    assert echoed == payload

    # Cleanup
    try:
        tunnel.stop_tunnel()
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)

