## Installing uv

This project is set up to use [**uv**](https://docs.astral.sh/uv/), the new package manager for Python. `uv` replaces traditional use of `pyenv`, `pipx`, `poetry`, `pip`, etc.

See [uv](https://docs.astral.sh/uv/getting-started/installation/) for help installing `uv`.

## Installing Python

`uv` will handle installing Python for us, but we can indicate a preferred version:

`uv python install 3.13`

Replace `3.13` with a preferred version. This template will force `3.11` or higher, but lower than `4.0`.

## Installing lawn-smart

Now that `uv` and Python are installed, we can install the project:

`uv sync`

That will:

1. Create a `.venv` folder at the root of the project (by default).
1. Install all required packages (as indicated in [pyproject.toml](./pyproject.toml)) into that virtual environment.
    - Includes `dev` dependencies

Make sure that your IDE (VSCode/PyCharm/etc.) know to use that [.venv](./.venv/) folder as the workspace folder for Python files.