from __future__ import annotations

import asyncio
import re
from typing import Optional, Tuple

import asyncssh

class Tunnel:
    """Encapsulates a localhost.run reverse SSH tunnel lifecycle.

    Usage:
        tunnel = Tunnel()
        public_url = tunnel.start("http://127.0.0.1:18080")
        ...
        tunnel.stop()

    Backward-compatible module-level helpers `start_tunnel` / `stop_tunnel` are retained.
    """

    def __init__(
        self,
        *,
        remote_host: str = "localhost.run",
        username: str = "nokey",
        remote_port: int = 80,
        keepalive_interval: int = 30,
        known_hosts: Optional[str] = None,
    ) -> None:
        self.remote_host = remote_host
        self.username = username
        self.remote_port = remote_port
        self.keepalive_interval = keepalive_interval
        self.known_hosts = known_hosts

        self.public_url: Optional[str] = None
        self.conn: Optional[asyncssh.SSHClientConnection] = None
        self.listener: Optional[asyncssh.SSHListener] = None
        self.proc: Optional[asyncssh.SSHClientProcess] = None

    async def _start_async(self, host: str, port: int) -> str:
        
        class BannerClient(asyncssh.SSHClient):
            def auth_banner_received(self, msg, lang):
                print(f"msg: {msg}")
                buf.put_nowait((msg, lang))
        
        buf = asyncio.Queue()
        self.conn = await asyncssh.connect(
            self.remote_host,
            username=self.username,
            known_hosts=self.known_hosts,
            keepalive_interval=self.keepalive_interval,
            client_factory=BannerClient,
        )
        
        self.listener = await self.conn.forward_local_port("", 80, host, port)
        
        public_url = None
        async with asyncio.timeout(20):
            while 1:
                msg, lang = await buf.get()
                m = re.search(r"https://[0-9a-f]+\.lhr\.life", msg)
                if m:
                    public_url = m.group(0)
                    break

        assert public_url is not None

        self.public_url = public_url
        print('\npublic url obtained:', public_url)
        return public_url

    def start(self, host: str, port: int) -> str:
        """Start the tunnel based on a local URL like http://HOST:PORT.

        Returns the public URL.
        """
        return asyncio.run(self._start_async(host, port))

    def stop(self) -> None:
        """Stop the tunnel if it is running."""
        if not (self.conn or self.listener or self.proc):
            return
        try:
            if self.proc:
                try:
                    self.proc.terminate()
                except Exception:
                    pass
            if self.listener:
                try:
                    async def _close() -> None:
                        if self.listener:
                            self.listener.close()
                    asyncio.run(_close())
                except Exception:
                    pass
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
        finally:
            self.proc = None
            self.listener = None
            self.conn = None
            self.public_url = None

    # Context manager support
    def __enter__(self) -> "Tunnel":
        """Enter context and return self. Call `start()` inside the block if needed."""
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        """Ensure tunnel is stopped on context exit. Exceptions are propagated."""
        try:
            self.stop()
        finally:
            # Returning False to propagate any exception
            return False

    # Convenience APIs mirroring previous module-level helpers
    def stop_tunnel(self) -> None:
        self.stop()

    @classmethod
    def start_tunnel(cls, host: str, port: int) -> Tuple[str, "Tunnel"]:
        t = cls()
        public_url = t.start(host, port)
        return public_url, t

