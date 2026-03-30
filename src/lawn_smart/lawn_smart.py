from typing import Annotated

import typer

from .core import GlobalCLIOptions, ProjectContext
from .devtools import app as devtools_cli
from .logging_config import get_console, verbosity_option

cli = typer.Typer(help="Main CLI for lawn-smart.")
console = get_console()

# !devtools should be the last subcommand added to ensure it appears at the end of the help output.
cli.add_typer(devtools_cli, name="devtools", help="Developer tools for lawn-smart.")


@cli.callback()
def main(
    ctx: ProjectContext,
    verbosity: Annotated[int, verbosity_option()] = 0,
    dry_run: Annotated[
        bool, typer.Option("-d", "--dry-run", help="Simulate actions without making changes.")
    ] = False,
) -> None:
    """Main entry point for the CLI, setting up global options and context."""
    ctx.obj = GlobalCLIOptions(verbosity=verbosity, dry_run=dry_run)


if __name__ == "__main__":
    cli()
