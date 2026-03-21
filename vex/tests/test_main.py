"""Tests for vex.main module."""

import os
from io import BytesIO
import argparse
from unittest.mock import patch
from typing import Any

import pytest

from vex import main
from vex.options import get_options
from vex.config import Vexrc
from vex import exceptions
from vex.tests.fakes import Object, make_fake_exists


class TestGetVexrc:
    def test_get_vexrc_nonexistent(self) -> None:
        options = get_options(["--config", "unlikely_to_exist"])
        with pytest.raises(exceptions.InvalidVexrc) as excinfo:
            main.get_vexrc(options, {})
        assert "unlikely_to_exist" in str(excinfo.value)

    def test_get_vexrc(self) -> None:
        options = get_options(["--config", "pretends_to_exist"])

        def fake_open(name: str, mode: str) -> BytesIO:
            assert name == "pretends_to_exist"
            assert mode == "rb"
            return BytesIO(b"a=b\n")

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", create=True, side_effect=fake_open),
        ):
            vexrc = main.get_vexrc(options, {})
            assert vexrc


class TestGetCwd:
    def test_get_cwd_no_option(self) -> None:
        options = argparse.Namespace(cwd=None)
        assert main.get_cwd(options) is None

    def test_get_cwd_nonexistent(self) -> None:
        options = argparse.Namespace(cwd="unlikely_to_exist")
        with patch("os.path.exists", return_value=False):
            with pytest.raises(exceptions.InvalidCwd):
                main.get_cwd(options)

    def test_get_cwd(self) -> None:
        options = argparse.Namespace(cwd="foo")
        with patch("os.path.exists", return_value=True):
            cwd = main.get_cwd(options)
        assert cwd == "foo"


class TestGetVirtualenvPath:
    def test_no_ve_base(self) -> None:
        with pytest.raises(exceptions.NoVirtualenvsDirectory):
            main.get_virtualenv_path("", "anything")

    def test_nonexistent_ve_base(self) -> None:
        with pytest.raises(exceptions.NoVirtualenvsDirectory):
            main.get_virtualenv_path("/unlikely_to_exist1", "anything")

    def test_no_ve_name(self) -> None:
        fake_path = os.path.abspath("pretends_to_exist")
        fake_exists = make_fake_exists([fake_path])
        with (
            patch("os.path.exists", side_effect=fake_exists),
            pytest.raises(exceptions.InvalidVirtualenv),
        ):
            main.get_virtualenv_path(fake_path, "")

    def test_nonexistent_ve_path(self) -> None:
        fake_path = os.path.abspath("pretends_to_exist")
        fake_exists = make_fake_exists([fake_path])
        with (
            patch("os.path.exists", side_effect=fake_exists),
            pytest.raises(exceptions.InvalidVirtualenv),
        ):
            main.get_virtualenv_path(fake_path, "/unlikely_to_exist2")

    def test_happy(self) -> None:
        fake_base = os.path.abspath("pretends_to_exist")
        fake_name = "also_pretend"
        fake_path = os.path.join(fake_base, fake_name)
        fake_exists = make_fake_exists([fake_base, fake_path])
        with patch("os.path.exists", side_effect=fake_exists):
            path = main.get_virtualenv_path(fake_base, fake_name)
            assert path == fake_path


class TestGetCommand:
    def test_shell_options(self) -> None:
        vexrc = Vexrc()
        vexrc[vexrc.default_heading]["shell"] = "/bin/dish"  # type: ignore
        options = Object(rest=["given", "command"])
        environ = {"SHELL": "wrong"}
        assert main.get_command(options, vexrc, environ) == ["given", "command"]

    def test_shell_vexrc(self) -> None:
        vexrc = Vexrc()
        vexrc[vexrc.default_heading]["shell"] = "/bin/dish"  # type: ignore
        options = Object(rest=None)
        environ = {"SHELL": "wrong"}
        assert main.get_command(options, vexrc, environ) == ["/bin/dish"]

    def test_shell_environ(self) -> None:
        vexrc = Vexrc()
        options = Object(rest=None)
        environ = {"SHELL": "/bin/dish"}
        assert main.get_command(options, vexrc, environ) == ["/bin/dish"]

    def test_nothing(self) -> None:
        vexrc = Vexrc()
        options = argparse.Namespace(rest=None)
        environ: dict[str, str] = {}
        with pytest.raises(exceptions.InvalidCommand):
            main.get_command(options, vexrc, environ)

    def test_flag(self) -> None:
        vexrc = Vexrc()
        options = argparse.Namespace(rest=["--foo"])
        environ: dict[str, str] = {}
        with pytest.raises(exceptions.InvalidCommand):
            main.get_command(options, vexrc, environ)
