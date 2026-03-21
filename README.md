# Vex

**Run a command in a virtualenv.**

Vex is an elegant, shell-agnostic tool for running commands inside virtual environments. Unlike traditional methods that rely on "activating" and "deactivating" environments by mutating your current shell's state, Vex simply launches a new process with the correct environment variables (like `PATH` and `VIRTUAL_ENV`) already set.

When the command finishes, the environment is gone. No cleanup, no `deactivate`, no shell-specific hacks.

## Modernization

Vex has been modernized to support the latest Python standards:

- **Python 3.12+ Required**: Leveraging modern features and built-in type safety.
- **UV Integration**: Vex now detects and uses [uv](https://github.com/astral-sh/uv) for lightning-fast virtualenv creation when using `--make`.
- **Pyproject.toml**: Fully migrated to modern PEP 517/518 packaging.
- **Type Safety**: The entire codebase is now fully type-hinted.

## How it works

`vex` runs any command in a virtualenv without modifying your current shell.

The standard way to use a virtualenv involves sourcing an `activate` script which modifies your shell's environment and adds a `deactivate` function. This is often brittle and shell-specific.

Vex takes a simpler approach: it calculates the environment required for the virtualenv and passes it directly to a new subprocess. This makes it naturally compatible with **bash, zsh, fish, PowerShell, cmd.exe**, and any other shell or executable.

## Examples

- `vex myenv bash`: Launch a bash shell with virtualenv `myenv` enabled. Exit the shell (Ctrl-D) to "deactivate".
- `vex myenv python`: Launch a Python interpreter inside virtualenv `myenv`.
- `vex myenv pip install requests`: Install a package into `myenv` without activating it.
- `vex -m ephemeral echo "Hello"`: Create a new virtualenv named `ephemeral`, run the command, and then immediately **remove** the virtualenv.
- `vex --path ./venv python script.py`: Run a script using a virtualenv located at a specific path.

## Installation

The recommended way to install Vex is using [uv](https://github.com/astral-sh/uv):

```bash
uv tool install vex
```

Alternatively, you can use pip:

```bash
pip install --user vex
```

### Usage with UV

Vex is designed to work seamlessly with `uv`. If `uv` is installed on your system, `vex --make` will automatically use `uv venv` to create environments, which is significantly faster than traditional `virtualenv`.

## Config

Vex looks for an optional configuration file at `~/.vexrc`.

```ini
shell=bash
virtualenvs=~/.virtualenvs
python=python3.12
env:
    ANSWER=42
```

- **shell**: The default shell to run if no command is provided (e.g., `vex myenv`).
- **virtualenvs**: The directory where your named virtualenvs are stored (defaults to `$WORKON_HOME` or `~/.virtualenvs`).
- **python**: The default Python executable to use when creating new environments with `--make`.
- **env**: Custom environment variables to inject into every Vex-managed process.

## Environment Variables

### WORKON_HOME

Vex uses the `WORKON_HOME` environment variable to determine where named virtual environments are stored. By default, this is `~/.virtualenvs`.

If you are using **uv** in a project and want Vex to target virtual environments local to your current directory (like a `.venv` folder), it is recommended to set `WORKON_HOME` to `./`:

```bash
export WORKON_HOME="./"
```

This allows you to use `vex .venv python` to run commands in your local project environment seamlessly.

## Shell Prompts

Vex does not automatically change your prompt. To see the current virtualenv in your prompt, you can use the `$VIRTUAL_ENV` variable in your shell configuration.

**Bash Example (~/.bashrc):**

```bash
function virtualenv_prompt() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "(${VIRTUAL_ENV##*/}) "
    fi
}
export PS1='$(virtualenv_prompt)\u@\H> '
```

## Shell Completion

Vex provides completion for virtualenv names. To enable it, add the following to your shell config:

**Bash (~/.bashrc):**
`eval "$(vex --shell-config bash)"`

**Zsh (~/.zshrc):**
`eval "$(vex --shell-config zsh)"`

**Fish (~/.config/fish/config.fish):**
`vex --shell-config fish | source`

## Development

Vex development is now managed with `uv`.

```bash
git clone https://github.com/sashahart/vex
cd vex
uv sync
uv run pytest
```
