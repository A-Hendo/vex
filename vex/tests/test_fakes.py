"""Tests for the fakes used in testing."""

import os
from vex.tests import fakes


def test_fake_environ() -> None:
    with fakes.FakeEnviron(FOO="bar") as env:
        assert env["FOO"] == "bar"
        assert os.environ["FOO"] == "bar"
    assert "FOO" not in os.environ


def test_patched_module() -> None:
    import os as os_mod
    original_exists = os_mod.path.exists
    with fakes.PatchedModule(os_mod.path, exists="fake"):
        assert os_mod.path.exists == "fake"  # type: ignore
    assert os_mod.path.exists == original_exists


def test_make_fake_exists() -> None:
    fake_exists = fakes.make_fake_exists(["/foo", "/bar"])
    assert fake_exists("/foo")
    assert fake_exists("/bar")
    assert not fake_exists("/baz")
