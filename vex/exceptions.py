"""Exceptions for vex."""


class InvalidArgument(Exception):
    """Base class for exceptions raised by anything under main()."""

    def __init__(self, message: str) -> None:
        self.message: str = message
        super().__init__(message)


class NoVirtualenvName(InvalidArgument):
    """No virtualenv name was given."""


class NoVirtualenvsDirectory(InvalidArgument):
    """There is no directory to find named virtualenvs in."""


class OtherShell(InvalidArgument):
    """The given argument to --shell-config is not recognized."""


class UnknownArguments(InvalidArgument):
    """Unknown arguments were given on the command line."""


class InvalidVexrc(InvalidArgument):
    """Config file specified or required but absent or unparseable."""


class InvalidVirtualenv(InvalidArgument):
    """No usable virtualenv was found."""


class InvalidCommand(InvalidArgument):
    """No runnable command was found."""


class InvalidCwd(InvalidArgument):
    """cwd specified or required but unusable."""


class BadConfig(InvalidArgument):
    """Fatal conditions encountered on the way to run."""


class VirtualenvAlreadyMade(InvalidArgument):
    """Virtualenv already exists."""


class VirtualenvNotMade(InvalidArgument):
    """Could not make virtualenv."""


class VirtualenvNotRemoved(InvalidArgument):
    """Virtualenv could not be removed."""


CommandNotFoundError = FileNotFoundError
