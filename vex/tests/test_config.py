"""Tests for vex.config module."""

import os
from io import BytesIO
from unittest.mock import patch

from vex import config
from vex.tests.fakes import FakeEnviron, PatchedModule, make_fake_exists


TYPICAL_VEXRC = b"""
shell=bash

env:
    ANSWER=42

arbitrary:
    x=y
"""

EXPAND_VEXRC = b"""
a="{SHELL}"
b='{SHELL}'
"""


class TestExtractHeading:
    """Make sure extract_heading works as intended."""

    def test_normal(self) -> None:
        assert config.extract_heading("foo:") == "foo"

    def test_trailing_space(self) -> None:
        assert config.extract_heading("foo: ") == "foo"

    def test_trailing_nonspace(self) -> None:
        assert config.extract_heading("foo: a") is None

    def test_no_colon(self) -> None:
        assert config.extract_heading("foo") is None


class TestExtractKeyValue:
    def test_normal(self) -> None:
        assert config.extract_key_value("foo=bar", {}) == ("foo", "bar")

    def test_no_equals(self) -> None:
        assert config.extract_key_value("foo", {}) is None


class TestParseVexrc:
    def test_error(self) -> None:
        stream = BytesIO(b"foo\n")
        # In Python 3.12+, we can't easily assign .name to BytesIO if it doesn't have it
        # but parse_vexrc uses getattr(inp, 'name', 'unknown')
        it = config.parse_vexrc(stream, {})
        rendered = ""
        try:
            next(it)
        except config.InvalidConfigError as error:
            rendered = str(error)
        assert rendered == "errors in 'unknown', lines [0]"

    def test_close(self) -> None:
        stream = BytesIO(b"a=b\nc=d\n")
        it = config.parse_vexrc(stream, {})
        next(it)
        it.close()


class TestVexrc:

    def test_read_nonexistent(self) -> None:
        vexrc = config.Vexrc()
        vexrc.read("unlikely_to_exist_1293", {})

    def test_read_empty(self) -> None:
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = BytesIO(b"")
            vexrc = config.Vexrc.from_file("stuff", {})
            assert vexrc["food"] is None

    def test_read_typical(self) -> None:
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = BytesIO(TYPICAL_VEXRC)
            vexrc = config.Vexrc.from_file("stuff", {})
            assert list(vexrc["root"].items()) == [("shell", "bash")]
            assert list(vexrc["env"].items()) == [("ANSWER", "42")]
            assert list(vexrc["arbitrary"].items()) == [("x", "y")]

    def test_read_expand(self) -> None:
        environ = {"SHELL": "smash"}
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = BytesIO(EXPAND_VEXRC)
            vexrc = config.Vexrc.from_file("stuff", environ)
            assert vexrc["root"] == {
                "a": "smash",
                "b": "{SHELL}",
            }

    def test_get_ve_base_in_vexrc_file(self) -> None:
        vexrc = config.Vexrc()
        root = vexrc.headings[vexrc.default_heading]

        fake_exists = make_fake_exists(["/specific/override"])
        root["virtualenvs"] = "/specific/override"
        with FakeEnviron(WORKON_HOME="tempting", HOME="nonsense"), PatchedModule(
            os.path, exists=fake_exists
        ):
            environ = {"WORKON_HOME": "/bad1", "HOME": "/bad2"}
            assert vexrc.get_ve_base(environ) == "/specific/override"

    def test_get_ve_base_not_in_vexrc_file_rather_workon_home(self) -> None:
        vexrc = config.Vexrc()
        root = vexrc.headings[vexrc.default_heading]
        assert "virtualenvs" not in root

        fake_exists = make_fake_exists(["/workon/home"])
        with FakeEnviron(WORKON_HOME="tempting", HOME="nonsense"), PatchedModule(
            os.path, exists=fake_exists
        ):
            environ = {"WORKON_HOME": "/workon/home", "HOME": "/bad"}
            assert vexrc.get_ve_base(environ) == "/workon/home"

    def test_get_ve_base_not_in_vexrc_file_rather_home(self) -> None:
        vexrc = config.Vexrc()
        root = vexrc.headings[vexrc.default_heading]
        assert "virtualenvs" not in root

        fake_exists = make_fake_exists(["/home/user", "/home/user/.virtualenvs"])
        with FakeEnviron(WORKON_HOME="tempting", HOME="nonsense"), PatchedModule(
            os.path, exists=fake_exists
        ):
            environ = {"HOME": "/home/user"}
            assert vexrc.get_ve_base(environ) == "/home/user/.virtualenvs"

    def test_get_ve_base_not_in_vexrc_no_keys(self) -> None:
        vexrc = config.Vexrc()
        root = vexrc.headings[vexrc.default_heading]
        assert "virtualenvs" not in root
        with FakeEnviron(WORKON_HOME="tempting", HOME="nonsense"), PatchedModule(
            os.path, expanduser=lambda p: ""
        ):
            environ: dict[str, str] = {}
            assert vexrc.get_ve_base(environ) == ""

    def test_get_ve_base_not_in_vexrc_no_values(self) -> None:
        vexrc = config.Vexrc()
        root = vexrc.headings[vexrc.default_heading]
        assert "virtualenvs" not in root
        with FakeEnviron(WORKON_HOME="tempting", HOME="nonsense"), PatchedModule(
            os.path, expanduser=lambda p: ""
        ):
            environ = {"WORKON_HOME": "", "HOME": ""}
            assert vexrc.get_ve_base(environ) == ""

    def test_ve_base_fake_windows(self) -> None:
        vexrc = config.Vexrc()
        environ = {"HOMEDRIVE": "C:", "HOMEPATH": "foo", "WORKON_HOME": ""}
        with patch("platform.system", return_value="Windows"), patch(
            "os.name", new="nt"
        ), patch("os.path.exists", return_value=True), patch(
            "os.path.isfile", return_value=False
        ):
            path = vexrc.get_ve_base(environ)
            import platform as plat
            assert plat.system() == "Windows"
            assert os.name == "nt"
            assert path
            assert path.startswith("C:")
