"""Virtualenv removal logic."""

import shutil
from typing import Optional

from vex import exceptions


def handle_remove(ve_path: Optional[str]) -> None:
    """Remove the virtualenv at the given path."""
    if not ve_path:
        return
    try:
        shutil.rmtree(ve_path)
    except Exception as error:
        raise exceptions.VirtualenvNotRemoved(
            f"could not remove virtualenv {ve_path!r}: {error}"
        )
