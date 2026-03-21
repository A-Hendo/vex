"""Test helper for temporary .vexrc files."""

import os
import tempfile
from typing import Any, Optional


class TempVexrcFile:
    def __init__(self, parent_dir: str, **kwargs: str):
        fd, self.path = tempfile.mkstemp(dir=parent_dir, suffix=".vexrc")
        with os.fdopen(fd, "w") as out:
            for key, value in kwargs.items():
                out.write(f"{key}={value}\n")
        self.file_path = self.path

    def close(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)

    def __enter__(self) -> "TempVexrcFile":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
