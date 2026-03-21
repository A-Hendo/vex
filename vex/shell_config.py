"""Shell configuration generation logic."""

import os
import re
import sys

from vex import config, exceptions

NOT_SCARY = re.compile(br"[~]?(?:[/]+[\w _,.][\w _\-,.]+)*\Z")


def scary_path(path: bytes) -> bool:
    """Whitelist the WORKON_HOME strings we're willing to substitute.

    If it smells at all bad, return True.
    """
    if not path:
        return True
    return not NOT_SCARY.match(path)


def shell_config_for(shell: str, vexrc: config.Vexrc, environ: dict[str, str]) -> bytes:
    """Return completion config for the named shell."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "shell_configs", shell)
    try:
        with open(path, "rb") as inp:
            data = inp.read()
    except FileNotFoundError:
        return b""

    ve_base = vexrc.get_ve_base(environ).encode("ascii")
    if ve_base and not scary_path(ve_base) and os.path.exists(ve_base):
        data = data.replace(b"$WORKON_HOME", ve_base)
    return data


def handle_shell_config(shell: str, vexrc: config.Vexrc, environ: dict[str, str]) -> int:
    """Carry out the logic of the --shell-config option."""
    data = shell_config_for(shell, vexrc, environ)
    if not data:
        raise exceptions.OtherShell(f"unknown shell: {shell!r}")

    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(data)
    else:
        # Fallback for unexpected environments, though Python 3.12+
        # should always have .buffer on standard streams.
        sys.stdout.write(data.decode("utf-8", errors="replace"))
    return 0
