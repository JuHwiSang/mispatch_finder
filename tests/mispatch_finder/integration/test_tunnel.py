import threading
import time
import queue
import secrets
import logging

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


def test_tunnel_does_not_break_logging(tmp_path, monkeypatch) -> None:
    # Configure root logger to write to a temp file
    log_fp = tmp_path / "tunnel_logging.jsonl"
    root = logging.getLogger()
    prev_handlers = list(root.handlers)
    prev_level = root.level
    for h in list(root.handlers):
        root.removeHandler(h)
    from mispatch_finder.shared.json_logging import build_json_file_handler
    fh = build_json_file_handler(log_fp, level=logging.INFO)
    root.setLevel(logging.INFO)
    root.addHandler(fh)

    try:
        logger = logging.getLogger(__name__)
        logger.info("before_marker", extra={"payload": {"type": "marker", "stage": "before"}})

        # Patch _launch to avoid real SSH/network while still exercising availability check
        def fake_launch(self, host: str, port: int, timeout_sec: float = 30.0) -> str:  # type: ignore[no-redef]
            self._ensure_ssh_available()
            return f"http://{host}:{port}"

        monkeypatch.setattr(Tunnel, "_launch", fake_launch, raising=True)

        public_url, handle = Tunnel.start_tunnel("127.0.0.1", 0)
        assert public_url.startswith("http://127.0.0.1:"), public_url
        logger.info("after_marker", extra={"payload": {"type": "marker", "stage": "after"}})

        # Cleanup
        handle.stop_tunnel()

        # Ensure logs were written both before and after start_tunnel
        for h in root.handlers:
            try:
                h.flush()
            except Exception:
                pass
        content = log_fp.read_text(encoding="utf-8")
        assert "before_marker" in content, "Log before start_tunnel not written"
        assert "after_marker" in content, "Log after start_tunnel not written"
    finally:
        # Restore previous logging config
        root.removeHandler(fh)
        root.setLevel(prev_level)
        for h in prev_handlers:
            root.addHandler(h)
