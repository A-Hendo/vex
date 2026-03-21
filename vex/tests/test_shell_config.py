"""Tests for vex.shell_config module."""

import os
from unittest.mock import patch
from typing import Dict

from vex.config import Vexrc
from vex.shell_config import scary_path as scary, shell_config_for


class TestShellConfigFor:
    def test_unknown_shell(self) -> None:
        vexrc = Vexrc()
        output = shell_config_for("unlikely_name", vexrc, {})
        assert output.strip() == b""

    def test_bash_config(self) -> None:
        vexrc = Vexrc()
        output = shell_config_for("bash", vexrc, {})
        assert output

    def test_zsh_config(self) -> None:
        vexrc = Vexrc()
        output = shell_config_for("zsh", vexrc, {})
        assert output

    def test_fish_config(self) -> None:
        vexrc = Vexrc()
        output = shell_config_for("fish", vexrc, {})
        assert output

    def test_bash_config_not_scary(self) -> None:
        vexrc = Vexrc()
        with patch("os.path.exists", return_value=True):
            output = shell_config_for("bash", vexrc, {"WORKON_HOME": "/hoorj"})
        assert output
        assert b"/hoorj" in output

    def test_zsh_config_not_scary(self) -> None:
        vexrc = Vexrc()
        with patch("os.path.exists", return_value=True):
            output = shell_config_for("zsh", vexrc, {"WORKON_HOME": "/hoorj"})
        assert output
        assert b"/hoorj" in output

    def test_fish_config_not_scary(self) -> None:
        vexrc = Vexrc()
        with patch("os.path.exists", return_value=True):
            output = shell_config_for("fish", vexrc, {"WORKON_HOME": "/hoorj"})
        assert output
        assert b"/hoorj" in output

    def test_bash_config_scary(self) -> None:
        vexrc = Vexrc()
        output = shell_config_for("bash", vexrc, {"WORKON_HOME": "$x"})
        assert output
        assert b"$x" not in output

    def test_zsh_config_scary(self) -> None:
        vexrc = Vexrc()
        output = shell_config_for("zsh", vexrc, {"WORKON_HOME": "$x"})
        assert output
        assert b"$x" not in output

    def test_fish_config_scary(self) -> None:
        vexrc = Vexrc()
        output = shell_config_for("fish", vexrc, {"WORKON_HOME": "$x"})
        assert output
        assert b"$x" not in output


class TestNotScary:
    """Test that scary_path does not puke on expected cases."""

    def test_normal(self) -> None:
        assert not scary(b"/home/user/whatever")
        assert not scary(b"/opt/weird/user/whatever")
        assert not scary(b"/foo")

    def test_underscore(self) -> None:
        assert not scary(b"/home/user/ve_place")

    def test_hyphen(self) -> None:
        assert not scary(b"/home/user/ve-place")

    def test_space(self) -> None:
        assert not scary(b"/home/user/ve place")

    def test_comma(self) -> None:
        assert not scary(b"/home/user/python,ruby/virtualenvs")

    def test_period(self) -> None:
        assert not scary(b"/home/user/.virtualenvs")


class TestScary:
    """Test that scary_path pukes on some known frightening cases."""

    def test_empty(self) -> None:
        assert scary(b"")

    def test_subshell(self) -> None:
        assert scary(b"$(rm anything)")

    def test_subshell_with_backticks(self) -> None:
        assert scary(b"`pwd`")

    def test_leading_double_quote(self) -> None:
        assert scary(b'"; rm anything; echo')
        assert scary(b'"')

    def test_variable_expansion(self) -> None:
        assert scary(b"$HOME")

    def test_variable_expansion_with_braces(self) -> None:
        assert scary(b"${HOME}")

    def test_variable_expansion_with_slash(self) -> None:
        assert scary(b"/${HOME}")

    def test_variable_expansion_with_slash_and_suffix(self) -> None:
        assert scary(b"/${HOME}/bar")

    def test_leading_single_quote(self) -> None:
        assert scary(b"' 'seems bad")
        assert scary(b"'")

    def test_trailing_backslash(self) -> None:
        assert scary(b"prefix\\")

    def test_leading_hyphen(self) -> None:
        assert scary(b"-delete")
        assert scary(b"--delete")

    def test_root(self) -> None:
        assert scary(b"/")
        assert scary(b"C:")
        assert scary(b"C:\\")

    def test_null(self) -> None:
        assert scary(b"\0")
        assert scary(b"\0b")
        assert scary(b"a\0b")
        assert scary(b"a\0")

    def test_newline(self) -> None:
        assert scary(b"/foo\nbar")
        assert scary(b"/foo\n/bar")

    def test_comment(self) -> None:
        assert scary(b"#foo")
        assert scary(b"stuff  # foo")

    def test_arithmetic_expansion(self) -> None:
        assert scary(b"$(( 2 + 2 ))")

    def test_integer_expansion(self) -> None:
        assert scary(b"$[ 2 + 2 ]")

    def test_lt(self) -> None:
        assert scary(b"<foo")

    def test_gt(self) -> None:
        assert scary(b">foo")

    def test_star(self) -> None:
        assert scary(b"*")

    def test_question_mark(self) -> None:
        assert scary(b"?")

    def test_here(self) -> None:
        assert scary(b"<<<")
        assert scary(b">>>")

    def test_semicolon(self) -> None:
        assert scary(b";")

    def test_or(self) -> None:
        assert scary(b"foo ||")

    def test_and(self) -> None:
        assert scary(b"foo &&")

    def test_background(self) -> None:
        assert scary(b"sleep 10 &")

    def test_pipeline(self) -> None:
        assert scary(b"| bar")
