"""Test helper for creating temporary virtualenvs."""

import os
import shutil
import subprocess
from typing import Any


class TempVenv:
    def __init__(self, parent: str, name: str, args: list[str] | None = None):
        assert os.path.abspath(parent) == parent
        self.parent = parent
        self.name = name
        self.args = args or []
        self.path = os.path.join(parent, name)
        self.open()

    def open(self) -> None:
        assert os.path.exists(self.parent)
        # Try uv first if available, otherwise virtualenv
        uv_path = shutil.which("uv")
        if uv_path:
            args = [uv_path, "venv", "--quiet", self.path] + self.args
        else:
            args = ["virtualenv", "--quiet", self.path] + self.args

        if not os.path.exists(self.path):
            subprocess.run(args, check=True)
        assert os.path.exists(self.path)

        if os.name == "nt":
            bin_path = os.path.join(self.path, "Scripts")
        else:
            bin_path = os.path.join(self.path, "bin")
        assert os.path.exists(bin_path)

    def close(self) -> None:
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
        assert not os.path.exists(self.path)

    def __enter__(self) -> "TempVenv":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
