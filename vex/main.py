"""Main command-line entry-point and any code tightly coupled to it."""

import os
import shutil
import sys
from typing import Any

from vex import config, exceptions
from vex._version import VERSION
from vex.make import handle_make
from vex.options import get_options
from vex.remove import handle_remove
from vex.run import get_environ, run
from vex.shell_config import handle_shell_config


def get_vexrc(options: Any, environ: dict[str, str]) -> config.Vexrc:
    """Get a representation of the contents of the config file."""
    # Complain if user specified nonexistent file with --config.
    # But we don't want to complain just because ~/.vexrc doesn't exist.
    if options.config and not os.path.exists(options.config):
        raise exceptions.InvalidVexrc(f"nonexistent config: {options.config!r}")
    filename = options.config or os.path.expanduser("~/.vexrc")
    vexrc = config.Vexrc.from_file(filename, environ)
    return vexrc


def get_cwd(options: Any) -> str | None:
    """Discover what directory the command should run in."""
    if not options.cwd:
        return None
    if not os.path.exists(options.cwd):
        raise exceptions.InvalidCwd(f"can't --cwd to invalid path {options.cwd!r}")
    return options.cwd


def get_virtualenv_name(options: Any) -> str:
    if options.path:
        return os.path.dirname(options.path)
    else:
        ve_name = options.rest.pop(0) if options.rest else ""
    if not ve_name:
        raise exceptions.NoVirtualenvName(
            "could not find a virtualenv name in the command line."
        )
    return ve_name


def get_virtualenv_path(ve_base: str, ve_name: str) -> str:
    """Check a virtualenv path, raising exceptions to explain problems."""
    if not ve_base:
        raise exceptions.NoVirtualenvsDirectory(
            "could not figure out a virtualenvs directory. "
            "make sure $HOME is set, or $WORKON_HOME,"
            " or set virtualenvs=something in your .vexrc"
        )

    # Using this requires get_ve_base to pass through nonexistent dirs
    if not os.path.exists(ve_base):
        message = (
            f"virtualenvs directory {ve_base!r} not found. "
            f"Create it or use vex --make to get started."
        )
        raise exceptions.NoVirtualenvsDirectory(message)

    if not ve_name:
        raise exceptions.InvalidVirtualenv("no virtualenv name")

    # n.b.: if ve_name is absolute, ve_base is discarded by os.path.join,
    # and an absolute path will be accepted as first arg.
    # So we check if they gave an absolute path as ve_name.
    # But we don't want this error if $PWD == $WORKON_HOME,
    # in which case "foo" is a valid relative path to virtualenv foo.
    ve_path = os.path.join(ve_base, ve_name)
    if ve_path == ve_name and os.path.basename(ve_name) != ve_name:
        raise exceptions.InvalidVirtualenv(
            f"To run in a virtualenv by its path, " f"use 'vex --path {ve_path}'"
        )

    ve_path = os.path.abspath(ve_path)
    if not os.path.exists(ve_path):
        raise exceptions.InvalidVirtualenv(f"no virtualenv found at {ve_path!r}.")
    return ve_path


def get_command(options: Any, vexrc: config.Vexrc, environ: dict[str, str]) -> list[str]:
    """Get a command to run."""
    command = options.rest
    if not command:
        command = vexrc.get_shell(environ)
    if command and command[0].startswith("--"):
        raise exceptions.InvalidCommand(
            f"don't put flags like {command[0]!r} after the virtualenv name."
        )
    if not command:
        raise exceptions.InvalidCommand("no command given")
    return command


def handle_version() -> int:
    sys.stdout.write(VERSION + "\n")
    return 0


def handle_list(ve_base: str, prefix: str = "") -> int:
    if not os.path.isdir(ve_base):
        sys.stderr.write(f"no virtualenvs directory at {ve_base!r}\n")
        return 1
    text = "\n".join(
        sorted(
            relative_path
            for relative_path in os.listdir(ve_base)
            if (not relative_path.startswith("-"))
            and relative_path.startswith(prefix)
            and os.path.isdir(os.path.join(ve_base, relative_path))
        )
    )
    sys.stdout.write(text + "\n")
    return 0


def _main(environ: dict[str, str], argv: list[str]) -> int:
    """Logic for main(), with less direct system interaction."""
    options = get_options(argv)
    if options.version:
        return handle_version()
    vexrc = get_vexrc(options, environ)
    # Handle --shell-config as soon as its arguments are available.
    if options.shell_to_configure:
        return handle_shell_config(options.shell_to_configure, vexrc, environ)
    if options.list is not None:
        return handle_list(vexrc.get_ve_base(environ), options.list)

    # Do as much as possible before a possible make, so errors can raise
    # without leaving behind an unused virtualenv.
    # get_virtualenv_name is destructive and must happen before get_command
    cwd = get_cwd(options)
    ve_base = vexrc.get_ve_base(environ)
    ve_name = get_virtualenv_name(options)
    command = get_command(options, vexrc, environ)
    # Either we create ve_path, get it from options.path or find it
    # in ve_base.
    if options.make:
        if options.path:
            make_path = os.path.abspath(options.path)
        else:
            make_path = os.path.abspath(os.path.join(ve_base, ve_name))
        if options.python is None:
            options.python = vexrc.get_default_python(environ)
            if options.python and not shutil.which(options.python):
                raise exceptions.InvalidVirtualenv(
                    f"the python specified in vexrc isn't executable: "
                    f"{options.python!r}"
                )
        elif not shutil.which(options.python):
            raise exceptions.InvalidVirtualenv(
                f"the python specified by --python isn't executable: "
                f"{options.python!r}"
            )
        handle_make(environ, options, make_path)
        ve_path = make_path
    elif options.path:
        ve_path = os.path.abspath(options.path)
        if not os.path.exists(ve_path) or not os.path.isdir(ve_path):
            raise exceptions.InvalidVirtualenv("argument for --path is not a directory")
    else:
        try:
            ve_path = get_virtualenv_path(ve_base, ve_name)
        except exceptions.NoVirtualenvName:
            options.print_help()
            raise

    # get_environ has to wait until ve_path is defined, which might
    # be after a make; of course we can't run until we have env.
    env = get_environ(environ, vexrc["env"] or {}, ve_path)
    returncode = run(command, env=env, cwd=cwd)
    if options.remove:
        handle_remove(ve_path)
    if returncode is None:
        raise exceptions.InvalidCommand(f"command not found: {command[0]!r}")
    return returncode


def main() -> None:
    """The main command-line entry point, with system interactions."""
    argv = sys.argv[1:]
    returncode = 1
    try:
        returncode = _main(dict(os.environ), argv)
    except exceptions.InvalidArgument as error:
        if error.message:
            sys.stderr.write(f"Error: {error.message}\n")
        else:
            raise
    sys.exit(returncode)
