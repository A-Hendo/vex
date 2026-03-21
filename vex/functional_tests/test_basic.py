"""Functional tests for vex."""

import logging
import os
import re
from subprocess import PIPE, Popen
from threading import Timer
from typing import Any

from vex.tests.tempdir import EmptyTempDir, TempDir
from vex.tests.tempvenv import TempVenv
from vex.tests.tempvexrcfile import TempVexrcFile

HERE = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(level=logging.DEBUG)


class Run:
    """Boilerplate for running a vex process with given parameters."""

    def __init__(
        self,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ):
        self.args = args or []
        self.env = env.copy() if env else {}
        self.timeout = timeout
        self.timer: Timer | None = None
        self.process: Popen[bytes] | None = None
        self.command_found: bool | None = None
        self.returned: int | None = None
        self.out: bytes | None = None
        self.err: bytes | None = None

    def start(self) -> None:
        env = self.env.copy()
        path = os.environ.get("PATH", "")
        env["PATH"] = path
        try:
            # We assume 'vex' is installed in the environment where tests run
            # or we could point to the one in the current source.
            # For simplicity, we assume 'vex' is on PATH.
            args = ["vex"] + self.args
            logging.debug("ARGS %r env %r", args, env)
            self.process = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
        except FileNotFoundError as error:
            if error.errno != 2:
                raise
            self.command_found = False
        else:
            if self.timeout is not None:
                self.timer = Timer(self.timeout, self.kill)
                self.timer.start()
            self.command_found = True

    def __enter__(self) -> "Run":
        self.start()
        return self

    def kill(self) -> None:
        if self.process:
            self.process.kill()

    def poll(self) -> None:
        if self.process:
            self.process.poll()
            self.returned = self.process.returncode

    def finish(self, inp: bytes | None = None) -> None:
        if self.process:
            out, err = self.process.communicate(inp)
            self.out = out
            self.err = err
            logging.debug("OUT %s", out.decode("utf-8", errors="replace"))
            logging.debug("ERR %s", err.decode("utf-8", errors="replace"))
            self.returned = self.process.returncode

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.timer:
            self.timer.cancel()
        if self.process and self.process.poll() is None:
            self.kill()


def test_runs_without_args() -> None:
    """vex without args should emit an error and return 1."""
    with Run([], timeout=1.0) as run:
        run.finish()
        assert run.command_found is True
        assert run.returned == 1


def test_help() -> None:
    """vex --help should emit help message."""
    with Run(["--help"], timeout=1.0) as run:
        run.finish()
        assert run.out is not None
        assert run.out.startswith(b"usage")
        assert b"--help" in run.out
        assert not run.err


def test_version() -> None:
    """vex --version should emit version string."""
    with Run(["--version"], timeout=1.0) as run:
        run.finish()
        assert run.out is not None
        match = re.match(br"^\d+\.\d+\.\d+\n$", run.out)
        assert match


def test_list() -> None:
    """vex --list should list available virtualenvs."""
    with TempDir() as ve_base:
        os.mkdir(os.path.join(ve_base.path, "foo"))
        os.mkdir(os.path.join(ve_base.path, "bar"))
        os.mkdir(os.path.join(ve_base.path, "-nope"))
        env = {"WORKON_HOME": ve_base.path}
        with Run(["--list"], env=env, timeout=1.0) as run:
            run.finish()
            assert not run.err
            assert b"bar\nfoo\n" in run.out if run.out else False


def test_list_no_ve_base() -> None:
    """vex --list with nonexistent ve_base should return 1."""
    nonexistent = "/tmp/whatever/foo/bar/nonexistent"
    env = {"WORKON_HOME": nonexistent}
    with Run(["--list"], env=env, timeout=1.0) as run:
        run.finish()
        assert run.returned == 1
        assert nonexistent.encode("utf-8") in (run.err or b"")


class TestShellConfig:
    def test_no_ve_base(self) -> None:
        env = {"WORKON_HOME": "/totally/nonexistent"}
        with Run(["--shell-config", "bash"], env=env, timeout=1.0) as run:
            run.finish()
            assert run.out
            assert not run.err

    def test_bash(self) -> None:
        env = {"WORKON_HOME": os.getcwd()}
        with Run(["--shell-config", "bash"], env=env, timeout=1.0) as run:
            run.finish()
            assert run.out
            assert not run.err


def test_find_with_HOME() -> None:
    with TempDir() as home:
        workon_home = os.path.join(home.path, ".virtualenvs")
        os.mkdir(workon_home)
        name = "vex_test_find_with_HOME"
        with TempVenv(workon_home, name, []):
            env = {"HOME": home.path}
            # Need to make sure 'vex' can find itself or is installed
            with Run([name, "echo", "foo"], env=env, timeout=5.0) as run:
                run.finish()
                assert run.command_found
                assert run.returned == 0
                assert b"foo" in (run.out or b"")


class TestWithVirtualenv:
    parent: TempDir
    venv: TempVenv

    @classmethod
    def setup_class(cls) -> None:
        cls.parent = TempDir()
        cls.venv = TempVenv(cls.parent.path, "vex_tests", [])

    @classmethod
    def teardown_class(cls) -> None:
        cls.venv.close()
        cls.parent.close()

    def test_find_with_WORKON_HOME(self) -> None:
        env = {"HOME": "ignore", "WORKON_HOME": self.parent.path}
        with Run([self.venv.name, "echo", "foo"], env=env, timeout=5.0) as run:
            run.finish()
            assert run.command_found
            assert run.returned == 0
            assert b"foo" in (run.out or b"")

    def test_find_with_path_option(self) -> None:
        with Run(["--path", self.venv.path, "echo", "foo"], timeout=5.0) as run:
            run.finish()
            assert run.command_found
            assert run.returned == 0
            assert b"foo" in (run.out or b"")

    def test_cwd_option(self) -> None:
        env = {"HOME": "ignore", "WORKON_HOME": self.parent.path}
        with EmptyTempDir() as cwd:
            with Run(
                ["--cwd", cwd.path, self.venv.name, "pwd"], env=env, timeout=5.0
            ) as run:
                run.finish()
                assert run.command_found
                assert run.returned == 0
                # On some systems pwd might return different format, but should contain cwd.path
                assert cwd.path.encode("utf-8") in (run.out or b"")


class TestMakeAndRemove:
    def test_make(self) -> None:
        with TempDir() as parent, TempDir() as home:
            env = {"HOME": home.path, "WORKON_HOME": parent.path}
            venv_name = "make_test"
            venv_path = os.path.join(parent.path, venv_name)
            with TempVexrcFile(home.path) as vexrc:
                with Run(["--make", venv_name, "echo", "42"], env=env, timeout=10.0) as run:
                    run.finish()
                    assert b"42" in (run.out or b"")
                    assert run.returned == 0
                    assert os.path.exists(venv_path)

    def test_remove(self) -> None:
        with TempDir() as parent, TempDir() as home:
            env = {"HOME": home.path, "WORKON_HOME": parent.path}
            with TempVenv(parent.path, "remove_test", []) as venv:
                assert os.path.exists(venv.path)
                with Run(["--remove", venv.name, "echo", "42"], env=env, timeout=10.0) as run:
                    run.finish()
                    assert b"42" in (run.out or b"")
                    assert run.returned == 0
                    assert not os.path.exists(venv.path)
