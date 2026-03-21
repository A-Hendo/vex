"""Config file processing (.vexrc)."""

import os
import platform
import re
import shlex
from collections import OrderedDict
from collections.abc import Generator
from pathlib import Path
from typing import Any

_IDENTIFIER_PATTERN = "[a-zA-Z][_a-zA-Z0-9]*"
_SQUOTE_RE = re.compile(r"'([^']*)'\Z")  # NO squotes inside
_DQUOTE_RE = re.compile(r'"([^"]*)"\Z')  # NO dquotes inside
_HEADING_RE = re.compile(rf"^({_IDENTIFIER_PATTERN}):[ \t\n\r]*\Z")
_VAR_RE = re.compile(rf"[ \t]*({_IDENTIFIER_PATTERN}) *= *(.*)[ \t\n\r]*$")


class InvalidConfigError(Exception):
    """Raised when there is an error during a .vexrc file parse."""

    def __init__(self, filename: str, errors: list[tuple[int, str]]):
        super().__init__()
        self.filename = filename
        self.errors = errors

    def __str__(self) -> str:
        return f"errors in {self.filename!r}, lines {[tup[0] for tup in self.errors]!r}"


class Vexrc:
    """Parsed representation of a .vexrc config file."""

    default_heading = "root"
    default_encoding = "utf-8"

    def __init__(self) -> None:
        self.encoding = self.default_encoding
        self.headings: dict[str, dict[str, str]] = OrderedDict()
        self.headings[self.default_heading] = OrderedDict()
        self.headings["env"] = OrderedDict()

    def __getitem__(self, key: str) -> dict[str, str] | None:
        return self.headings.get(key)

    @classmethod
    def from_file(cls, path: str, environ: dict[str, str]) -> "Vexrc":
        """Make a Vexrc instance from given file in given environ."""
        instance = cls()
        instance.read(path, environ)
        return instance

    def read(self, path: str, environ: dict[str, str]) -> None:
        """Read data from file into this vexrc instance."""
        try:
            with open(path, "rb") as inp:
                parsing = parse_vexrc(inp, environ)
                for heading, key, value in parsing:
                    heading = self.default_heading if heading is None else heading
                    if heading not in self.headings:
                        self.headings[heading] = OrderedDict()
                    self.headings[heading][key] = value
        except FileNotFoundError:
            return None

    def get_ve_base(self, environ: dict[str, str]) -> str:
        """Find a directory to look for virtualenvs in."""
        # set ve_base to a path we can look for virtualenvs:
        # 1. .vexrc
        # 2. WORKON_HOME (as defined for virtualenvwrapper's benefit)
        # 3. $HOME/.virtualenvs
        ve_base_value = self.headings[self.default_heading].get("virtualenvs")
        if ve_base_value:
            ve_base = os.path.expanduser(ve_base_value)
        else:
            ve_base = environ.get("WORKON_HOME", "")

        if not ve_base:
            if platform.system() == "Windows":
                _win_drive = environ.get("HOMEDRIVE", "")
                home_path = environ.get("HOMEPATH", "")
                if home_path:
                    home = os.path.join(_win_drive, home_path)
                else:
                    home = os.path.expanduser("~")
            else:
                home = environ.get("HOME", "")
                if not home:
                    home = os.path.expanduser("~")

            if not home:
                return ""
            ve_base = os.path.join(home, ".virtualenvs")

        return ve_base

    def get_shell(self, environ: dict[str, str]) -> list[str] | None:
        """Find a command to run."""
        command = self.headings[self.default_heading].get("shell")
        if not command and os.name != "nt":
            command = environ.get("SHELL", "")
        return shlex.split(command) if command else None

    def get_default_python(self, environ: dict[str, str]) -> str | None:
        """Find a command to run."""
        return self.headings[self.default_heading].get("python")


def extract_heading(line: str) -> str | None:
    """Return heading in given line or None if it's not a heading."""
    match = _HEADING_RE.match(line)
    return match.group(1) if match else None


def extract_key_value(line: str, environ: dict[str, str]) -> tuple[str, str] | None:
    """Return key, value from given line if present, else return None."""
    segments = line.split("=", 1)
    if len(segments) < 2:
        return None
    key, value = segments
    value = value.strip()
    if value:
        if value.startswith("'") and _SQUOTE_RE.match(value):
            value = value[1:-1]
        elif value.startswith('"') and _DQUOTE_RE.match(value):
            template = value[1:-1]
            try:
                value = template.format(**environ)
            except KeyError:
                # Fallback to literal if env var missing?
                pass
        value = value.strip()
    key = key.strip()
    return key, value


def parse_vexrc(
    inp: Any, environ: dict[str, str]
) -> Generator[tuple[str | None, str, str], None, None]:
    """Iterator yielding key/value pairs from given stream."""
    heading = None
    errors = []
    for line_number, line_bytes in enumerate(inp):
        line = line_bytes.decode("utf-8")
        if not line.strip():
            continue
        extracted_heading = extract_heading(line)
        if extracted_heading is not None:
            heading = extracted_heading
            continue
        kv_tuple = extract_key_value(line, environ)
        if kv_tuple is None:
            errors.append((line_number, line))
            continue
        yield heading, kv_tuple[0], kv_tuple[1]

    if errors:
        raise InvalidConfigError(getattr(inp, "name", "unknown"), errors)
