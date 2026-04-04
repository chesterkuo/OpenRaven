from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def is_cloudflared_available() -> bool:
    return shutil.which("cloudflared") is not None


def save_tunnel_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(str(pid), encoding="utf-8")


def get_tunnel_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def clear_tunnel_pid(pid_file: Path) -> None:
    if pid_file.exists():
        pid_file.unlink()


def save_tunnel_url(url_file: Path, url: str) -> None:
    url_file.write_text(url, encoding="utf-8")


def get_tunnel_url(url_file: Path) -> str:
    if not url_file.exists():
        return ""
    return url_file.read_text(encoding="utf-8").strip()


def start_tunnel(port: int, working_dir: Path) -> str:
    """Start a Cloudflare Tunnel and return the public URL."""
    if not is_cloudflared_available():
        raise RuntimeError(
            "cloudflared is not installed. Install it:\n"
            "  macOS: brew install cloudflared\n"
            "  Linux: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
        )

    pid_file = working_dir / "tunnel.pid"
    url_file = working_dir / "tunnel_url"
    stop_tunnel(working_dir)

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )

    save_tunnel_pid(pid_file, proc.pid)

    import re
    import time
    url = ""
    deadline = time.time() + 15
    while time.time() < deadline:
        line = proc.stderr.readline().decode("utf-8", errors="replace")
        match = re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", line)
        if match:
            url = match.group(1)
            break

    if not url:
        logger.warning("Could not detect tunnel URL within timeout")
        url = f"tunnel-starting (PID {proc.pid})"

    save_tunnel_url(url_file, url)
    logger.info(f"Tunnel started: {url} (PID {proc.pid})")
    return url


def stop_tunnel(working_dir: Path) -> bool:
    pid_file = working_dir / "tunnel.pid"
    url_file = working_dir / "tunnel_url"

    pid = get_tunnel_pid(pid_file)
    if pid is None:
        return False

    try:
        os.kill(pid, signal.SIGTERM)
        logger.info(f"Stopped tunnel (PID {pid})")
    except ProcessLookupError:
        logger.info(f"Tunnel process {pid} already stopped")
    except PermissionError:
        logger.warning(f"Cannot stop tunnel process {pid} (permission denied)")
        return False

    clear_tunnel_pid(pid_file)
    if url_file.exists():
        url_file.unlink()
    return True
