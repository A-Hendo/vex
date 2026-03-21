"""Run subprocess."""

import os
import platform
import shutil
import subprocess

from vex import exceptions


def get_environ(
    environ: dict[str, str], defaults: dict[str, str], ve_path: str
) -> dict[str, str]:
    """Make an environment to run with."""
    # Copy the parent environment, add in defaults from .vexrc.
    env: dict[str, str] = environ.copy()
    env.update(defaults)

    # Leaving in existing PYTHONHOME can cause some errors
    if "PYTHONHOME" in env:
        del env["PYTHONHOME"]

    # Now we have to adjust PATH to find scripts for the virtualenv...
    # PATH being unset/empty is OK, but ve_path must be set
    # or there is nothing for us to do here and it's bad.
    if not ve_path:
        raise exceptions.BadConfig("ve_path must be set")
    ve_bin: str = ""
    if platform.system() == "Windows":
        ve_bin = os.path.join(ve_path, "Scripts")
    else:
        ve_bin = os.path.join(ve_path, "bin")

    # If user is currently in a virtualenv, DON'T just prepend
    # to its path (vex foo; echo $PATH -> " /foo/bin:/bar/bin")
    # but don't incur this cost unless we're already in one.
    # activate handles this by running "deactivate" first, we don't
    # have that so we have to use other ways.
    # This would not be necessary and things would be simpler if vex
    # did not have to interoperate with a ubiquitous existing tool.
    # virtualenv doesn't...
    current_ve: str = env.get("VIRTUAL_ENV", "")
    system_path: str = environ.get("PATH", "")
    segments: list[str] = system_path.split(os.pathsep)
    if current_ve:
        # Since activate doesn't export _OLD_VIRTUAL_PATH, we are going to
        # manually remove the virtualenv's bin.
        # A virtualenv's bin should not normally be on PATH except
        # via activate or similar, so I'm OK with this solution.
        current_ve_bin: str = os.path.join(current_ve, "bin")
        try:
            segments.remove(current_ve_bin)
        except ValueError:
            raise exceptions.BadConfig(
                f"something set VIRTUAL_ENV prior to this vex execution, "
                f"implying that a virtualenv is already activated "
                f"and PATH should contain the virtualenv's bin directory. "
                f"Unfortunately, it doesn't: it's {system_path!r}. "
                f"You might want to check that PATH is not "
                f"getting clobbered somewhere, e.g. in your shell's configs."
            )

    segments.insert(0, ve_bin)
    env["PATH"] = os.pathsep.join(segments)
    env["VIRTUAL_ENV"] = ve_path
    return env


def run(command: list[str], env: dict[str, str], cwd: str | None) -> int | None:
    """Run the given command."""
    assert command
    if cwd:
        assert os.path.exists(cwd)
    if platform.system() == "Windows":
        exe: str | None = shutil.which(command[0], path=env["PATH"])
        if exe:
            command[0] = exe
    _, command_name = os.path.split(command[0])
    if command_name in ("bash", "zsh") and "VIRTUALENVWRAPPER_PYTHON" not in env:
        env["VIRTUALENVWRAPPER_PYTHON"] = ":"
    try:
        process: subprocess.Popen[bytes] = subprocess.Popen(command, env=env, cwd=cwd)
        process.wait()
    except OSError as error:
        if error.errno != 2:
            raise
        return None
    return int(process.returncode) if process.returncode is not None else None
