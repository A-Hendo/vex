"""Virtualenv removal logic."""

import shutil

from vex import exceptions


def handle_remove(ve_path: str | None) -> None:
    """Remove the virtualenv at the given path."""
    if not ve_path:
        return
    try:
        shutil.rmtree(ve_path)
    except Exception as error:
        raise exceptions.VirtualenvNotRemoved(
            f"could not remove virtualenv {ve_path!r}: {error}"
        )
