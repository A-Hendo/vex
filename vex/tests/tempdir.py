"""Test helper for temporary directories."""

import os
import shutil
import tempfile
from typing import Any


class TempDir:
    def __init__(self) -> None:
        self.path = tempfile.mkdtemp()

    def close(self) -> None:
        if os.path.exists(self.path):
            shutil.rmtree(self.path)

    def __enter__(self) -> "TempDir":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()


class EmptyTempDir(TempDir):
    """Alias for TempDir for clarity in some tests."""
    pass
