"""Fakes for testing."""

import os
from typing import Any


class Object:
    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            if key.startswith("_"):
                continue
            setattr(self, key, value)


class FakePopen:
    def __init__(self, returncode: int = 888):
        self.command: list[str] | None = None
        self.env: dict[str, str] | None = None
        self.cwd: str | None = None
        self.waited = False
        self.expected_returncode = returncode
        self.returncode: int | None = None

    def __call__(
        self,
        command: list[str],
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> "FakePopen":
        self.command = command
        self.env = env
        self.cwd = cwd
        return self

    def wait(self) -> None:
        self.waited = True
        self.returncode = self.expected_returncode


class FakeEnviron:
    def __init__(self, **kwargs: str):
        self.original: dict[str, str] | None = None
        self.kwargs = kwargs

    def __enter__(self) -> dict[str, str]:
        self.original = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.kwargs)
        return dict(os.environ)

    def __exit__(self, typ: Any, value: Any, tb: Any) -> None:
        if self.original is not None:
            os.environ.clear()
            os.environ.update(self.original)
        self.original = None


class PatchedModule:
    def __init__(self, module: Any, **kwargs: Any):
        self.module = module
        self.originals: dict[str, Any] | None = None
        self.kwargs = kwargs

    def __enter__(self) -> Any:
        self.originals = {
            key: getattr(self.module, key, None) for key in self.kwargs.keys()
        }
        for key, value in self.kwargs.items():
            setattr(self.module, key, value)
        return self.module

    def __exit__(self, typ: Any, value: Any, tb: Any) -> None:
        if self.originals is not None:
            for key, value in self.originals.items():
                setattr(self.module, key, value)
        self.originals = None


def make_fake_exists(accepted_paths: list[str]) -> Any:
    """Make functions which only return true for a particular string."""
    assert not isinstance(accepted_paths, str)

    def fake_exists(path: str) -> bool:
        return path in accepted_paths

    return fake_exists
