from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

class Tunnel:
    """Subprocess-backed tunnel using `ssh` to localhost.run.

    Opens a reverse tunnel via: ssh -R REMOTE:host:port nokey@localhost.run
    Parses the public URL from ssh stdout.
    """

    def __init__(
        self,
        *,
        remote_host: str = "localhost.run",
        username: str = "nokey",
        remote_port: int = 80,
        keepalive_interval: int = 30,
        known_hosts: str | None = None,
    ) -> None:
        self.remote_host = remote_host
        self.username = username
        self.remote_port = remote_port
        self.keepalive_interval = keepalive_interval
        self.known_hosts = known_hosts

        self.public_url: str | None = None
        self._proc: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._stop_event = threading.Event()

    @staticmethod
    def _ensure_ssh_available() -> None:
        if shutil.which("ssh") is None:
            raise RuntimeError(
                "`ssh` not found. Please install OpenSSH client and ensure `ssh` is in PATH."
            )

    def _build_cmd(self, host: str, port: int) -> list[str]:
        # Force non-interactive, robust behavior across environments
        #  - BatchMode=yes: never prompt for passwords/confirmation
        #  - StrictHostKeyChecking=no: accept host key without prompt
        #  - UserKnownHostsFile: avoid writing to user's known_hosts (use provided path or OS devnull)
        #  - ServerAliveInterval: keep tunnel alive with periodic keepalives
        #  - ExitOnForwardFailure=yes: fail fast if remote forward cannot be established
        known_hosts_file = self.known_hosts if self.known_hosts else os.devnull
        base = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            f"UserKnownHostsFile={known_hosts_file}",
            "-o",
            f"ServerAliveInterval={self.keepalive_interval}",
            "-o",
            "ExitOnForwardFailure=yes",
            "-R",
            f"{self.remote_port}:{host}:{port}",
            f"{self.username}@{self.remote_host}",
        ]
        return base

    def _launch(self, host: str, port: int, timeout_sec: float = 30.0) -> str:
        self._ensure_ssh_available()
        cmd = self._build_cmd(host, port)
        logger.info("tunnel_exec", extra={
            "payload": {
                "type": "tunnel_exec",
                "cmd": " ".join(cmd),
            }
        })
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self._proc = proc

        def _reader() -> None:
            assert proc.stdout is not None
            for raw in proc.stdout:
                if self._stop_event.is_set():
                    break
                line = raw.strip()
                logger.debug("tunnel_ssh_line", extra={
                    "payload": {"type": "ssh_line", "line": line}
                })
                m = re.search(r"https://[0-9a-f]+\.lhr\.life", line)
                if m and not self.public_url:
                    self.public_url = m.group(0)
                    break

        self._reader = threading.Thread(target=_reader, daemon=True)
        self._reader.start()

        start = time.time()
        while self.public_url is None and proc.poll() is None:
            if time.time() - start > timeout_sec:
                break
            time.sleep(0.05)

        if self.public_url:
            logger.info("tunnel_ready", extra={
                "payload": {
                    "type": "tunnel_ready",
                    "public_url": self.public_url,
                }
            })
            print("\npublic url obtained:", self.public_url)
            return self.public_url

        # Failed to obtain URL; clean up and error
        self.stop()
        logger.error("tunnel_failed_to_obtain_url", extra={
            "payload": {
                "type": "tunnel_error",
                "reason": "no_public_url",
            }
        })
        raise RuntimeError("Failed to obtain public URL from ssh output. Is localhost.run reachable?")

    def start(self, host: str, port: int) -> str:
        return self._launch(host, port)

    def stop(self) -> None:
        self._stop_event.set()
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        finally:
            self._proc = None
            if self._reader is not None:
                self._reader.join(timeout=2)
                self._reader = None
            self.public_url = None

    # Context manager support
    def __enter__(self) -> "Tunnel":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            self.stop()
        finally:
            return False

    # Convenience APIs mirroring previous module-level helpers
    def stop_tunnel(self) -> None:
        self.stop()

    @classmethod
    def start_tunnel(cls, host: str, port: int) -> Tuple[str, "Tunnel"]:
        t = cls()
        public_url = t.start(host, port)
        return public_url, t

