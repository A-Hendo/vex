"""Tests for vex.run module."""

import os
import platform
import subprocess
from unittest.mock import patch

import pytest

from vex import exceptions, run
from vex.tests.fakes import FakeEnviron, FakePopen, PatchedModule


def test_get_environ() -> None:
    path = "thing"
    defaults = {"from_defaults": "b"}
    original = {
        "PATH": os.path.pathsep.join(["crap", "bad_old_ve/bin", "junk"]),
        "from_passed": "x",
        "PYTHONHOME": "removeme",
        "VIRTUAL_ENV": "bad_old_ve",
    }
    passed_environ = original.copy()
    with FakeEnviron() as os_environ, PatchedModule(os.path, exists=lambda path: True):
        result = run.get_environ(passed_environ, defaults, path)
        # os.environ should not be changed in any way.
        assert len(os_environ) == 0
    # nor should the passed environ be changed in any way.
    assert sorted(original.items()) == sorted(passed_environ.items())
    # but result should inherit from passed
    assert result["from_passed"] == "x"
    # and should update from defaults
    assert result["from_defaults"] == "b"
    # except with no PYTHONHOME
    assert "PYTHONHOME" not in result
    # and PATH is prepended to. but without bad old ve's bin.
    # Note: run.py uses os.path.join(ve_path, "bin") which will use / or \
    expected_bin = os.path.join("thing", "bin")
    assert result["PATH"] == os.path.pathsep.join([expected_bin, "crap", "junk"])
    assert result["VIRTUAL_ENV"] == path


def test_run() -> None:
    # mock subprocess.Popen because we are cowards
    with PatchedModule(os.path, exists=lambda path: True), PatchedModule(
        subprocess, Popen=FakePopen(returncode=888)
    ) as mod:
        assert not mod.Popen.waited
        command = ["foo"]
        env = {"this": "irrelevant"}
        cwd = "also_irrelevant"
        returncode = run.run(command, env=env, cwd=cwd)
        assert mod.Popen.waited
        assert mod.Popen.command == command
        assert mod.Popen.env == env
        assert mod.Popen.cwd == cwd
        assert returncode == 888


def test_run_bad_command() -> None:
    env = os.environ.copy()
    # On most systems this won't be found
    returncode = run.run(["blah_unlikely_command_12345"], env=env, cwd=".")
    assert returncode is None


class TestGetEnviron:
    def test_ve_path_None(self) -> None:
        with pytest.raises(exceptions.BadConfig):
            run.get_environ({}, {}, None)  # type: ignore

    def test_ve_path_empty_string(self) -> None:
        with pytest.raises(exceptions.BadConfig):
            run.get_environ({}, {}, "")

    def test_copies_original(self) -> None:
        original = {"foo": "bar"}
        defaults: dict[str, str] = {}
        ve_path = "blah"
        with patch("os.path.exists", return_value=True):
            environ = run.get_environ(original, defaults, ve_path)
        assert environ is not original
        assert environ.get("foo") == "bar"

    def test_updates_with_defaults(self) -> None:
        original = {"foo": "bar", "yak": "nope"}
        defaults = {"bam": "pow", "yak": "fur"}
        ve_path = "blah"
        with patch("os.path.exists", return_value=True):
            environ = run.get_environ(original, defaults, ve_path)
        assert environ.get("bam") == "pow"
        assert environ.get("yak") == "fur"

    def test_ve_path(self) -> None:
        original: dict[str, str] = {"foo": "bar"}
        defaults: dict[str, str] = {}
        ve_path = "blah"
        with patch("os.path.exists", return_value=True):
            environ = run.get_environ(original, defaults, ve_path)
        assert environ.get("VIRTUAL_ENV") == ve_path

    def test_prefixes_PATH(self) -> None:
        original: dict[str, str] = {"foo": "bar"}
        defaults: dict[str, str] = {}
        ve_path = "fnood"
        bin_path = os.path.join(ve_path, "bin")
        with patch("os.path.exists", return_value=True):
            environ = run.get_environ(original, defaults, ve_path)
        path_env = environ.get("PATH", "")
        paths = path_env.split(os.pathsep)
        assert paths[0] == bin_path

    def test_removes_old_virtualenv_bin_path(self) -> None:
        new = "new"
        old = "old"
        original = {"foo": "bar", "VIRTUAL_ENV": old, "PATH": f"{old}/bin:other"}
        defaults: dict[str, str] = {}
        new_bin = os.path.join(new, "bin")
        old_bin = os.path.join(old, "bin")
        with patch("os.path.exists", return_value=True):
            environ = run.get_environ(original, defaults, new)
        path_env = environ.get("PATH", "")
        paths = path_env.split(os.pathsep)
        assert paths[0] == new_bin
        assert old_bin not in paths

    def test_fake_windows_env(self) -> None:
        # does not simulate different os.pathsep, etc.
        # just tests using Script instead of bin, for coverage.
        original: dict[str, str] = {"foo": "bar"}
        defaults: dict[str, str] = {}
        ve_path = "fnard"
        bin_path = os.path.join(ve_path, "Scripts")
        with patch("platform.system", return_value="Windows"), patch(
            "os.path.exists", return_value=True
        ):
            assert platform.system() == "Windows"
            environ = run.get_environ(original, defaults, ve_path)
        assert environ.get("VIRTUAL_ENV") == ve_path
        path_env = environ.get("PATH", "")
        paths = path_env.split(os.pathsep)
        assert paths[0] == bin_path
