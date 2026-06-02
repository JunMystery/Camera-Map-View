"""Launch a user-visible operating-system ping session for one camera."""

import platform
import subprocess

from utils.validators import is_valid_ipv4


def open_active_ping(ip_address: str) -> bool:
    """Open a terminal ping that runs until the user closes it."""
    if not is_valid_ipv4(ip_address):
        return False
    try:
        if platform.system().lower() == "windows":
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            subprocess.Popen(["cmd.exe", "/k", "ping", "-t", ip_address], creationflags=creationflags)
            return True
        subprocess.Popen(["ping", ip_address])
        return True
    except OSError:
        return False
