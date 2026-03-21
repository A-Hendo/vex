"""Virtualenv creation logic."""

import os
import shutil
import sys
from typing import Any

from vex import exceptions
from vex.run import run

PYDOC_SCRIPT: bytes = """#!/usr/bin/env python
from pydoc import cli
cli()
""".encode("ascii")


PYDOC_BATCH: bytes = """
@python -m pydoc %*
""".encode("ascii")


def handle_make(environ: dict[str, str], options: Any, make_path: str) -> None:
    """Create a virtualenv at the given path."""
    if os.path.exists(make_path):
        # Can't ignore existing virtualenv happily because existing one
        # might have different parameters and --make implies nonexistent
        raise exceptions.VirtualenvAlreadyMade(
            f"virtualenv already exists: {make_path!r}"
        )

    ve_base: str = os.path.dirname(make_path)
    if not os.path.exists(ve_base):
        os.makedirs(ve_base, exist_ok=True)
    elif not os.path.isdir(ve_base):
        raise exceptions.VirtualenvNotMade(
            f"could not make virtualenv: "
            f"{ve_base!r} already exists but is not a directory. "
            f"Choose a different virtualenvs path using ~/.vexrc "
            f"or $WORKON_HOME, or remove the existing file; "
            f"then rerun your vex --make command."
        )

    # Strategy for creation:
    # 1. If uv is available, use 'uv venv' (it's fastest)
    # 2. Otherwise use 'virtualenv'
    # TODO: add an option to force 'venv' stdlib

    uv_path: str | None = shutil.which("uv")
    args: list[str] = []
    if uv_path:
        args = [uv_path, "venv", make_path]
        if options.python:
            args += ["--python", options.python]
        if options.site_packages:
            args += ["--system-site-packages"]
        # uv doesn't have an exact 'always-copy' equivalent in 'venv' command
        # but it uses symlinks/hardlinks/clones by default.
    else:
        # Fallback to virtualenv
        ve: str = ""
        if os.name == "nt" and not os.environ.get("VIRTUAL_ENV", ""):
            ve = os.path.join(
                os.path.dirname(sys.executable), "Scripts", "virtualenv"
            )
        else:
            ve = "virtualenv"
        args = [ve, make_path]
        if options.python:
            if os.name == "nt":
                python: str | None = shutil.which(options.python)
                if python:
                    options.python = python
            args += ["--python", options.python]
        if options.site_packages:
            args += ["--system-site-packages"]
        if options.always_copy:
            args += ["--always-copy"]

    returncode: int | None = run(args, env=environ, cwd=ve_base)
    if returncode != 0:
        raise exceptions.VirtualenvNotMade("error creating virtualenv")

    # Install pydoc shim
    pydoc_path: str = ""
    if os.name != "nt":
        pydoc_path = os.path.join(make_path, "bin", "pydoc")
        if os.path.exists(os.path.dirname(pydoc_path)):
            with open(pydoc_path, "wb") as out:
                out.write(PYDOC_SCRIPT)
            perms: int = os.stat(pydoc_path).st_mode
            os.chmod(pydoc_path, perms | 0o0111)
    else:
        pydoc_path = os.path.join(make_path, "Scripts", "pydoc.bat")
        with open(pydoc_path, "wb") as out:
            out.write(PYDOC_BATCH)
