import abc
from pathlib import Path
from typing import Annotated, ClassVar

import typer
from jinja2 import Environment, PackageLoader, Template

from .core import ProjectContext
from .logging_config import get_console, get_logger

logger = get_logger(__name__)
app = typer.Typer(help="Developer tools for lawn-smart.")
console = get_console()

PACKAGE_ROOT = Path(__file__).resolve().parent

jinja_env = Environment(loader=PackageLoader(PACKAGE_ROOT.stem, package_path="devtools_templates"))


class FileTemplate(abc.ABC):
    """Abstract base class for file templates, defining the interface for generating file content."""

    TEMPLATE: ClassVar[str]

    def get_template(self) -> Template:
        """Load the Jinja2 template for this file type."""
        return jinja_env.get_template(self.TEMPLATE)

    def generate_content(self) -> str:
        """Generate the content for the file by rendering the template with appropriate context."""
        template = self.get_template()
        return template.render(package_root=PACKAGE_ROOT.stem)


class InitFile(FileTemplate):
    """Marker dataclass for __init__.py files, allowing for potential future metadata or methods related to package initialization."""

    TEMPLATE: ClassVar[str] = "__init__.py.j2"


class ModuleFile(FileTemplate):
    """A module file to be created, encapsulating the content generation logic."""

    TEMPLATE: ClassVar[str] = "module.py.j2"


def normalize_target(module_path: str, package: bool = False) -> Path:
    """Convert a dotted module path or filesystem path into an absolute Path within the package.

    Args:
        module_path: The input module path, either in dotted form (e.g., "reports.new.module") or as a filesystem path (e.g., "reports/new/module.py").
        package: If True, ensures the target is treated as a package (i.e., ends with __init__.py).

    Returns:
        An absolute Path object pointing to the target module file within the package.
    """
    module_path = module_path.strip()
    if package and module_path.lower().endswith(".py"):
        raise typer.BadParameter(
            "Cannot specify a .py file when creating a package. Use a dotted path without .py extension."
        )
    module_path = module_path.strip().rstrip(".py")
    path = Path(module_path.replace(".", "/"))
    if package and not path.name.endswith("__init__"):
        path /= "__init__.py"
    path = path.with_suffix(".py")
    return path if path.is_absolute() else PACKAGE_ROOT / path


def _ensure_package_inits(target: Path, *, dry_run: bool = False) -> None:
    relative_parts = target.relative_to(PACKAGE_ROOT).parts[:-1]
    current = PACKAGE_ROOT
    for part in relative_parts:
        current /= part
        if not dry_run:
            current.mkdir(parents=True, exist_ok=True)
            init_file = current / "__init__.py"
            if not init_file.exists():
                _ = init_file.write_text(InitFile().generate_content(), encoding="utf-8")
        else:
            console.log(f"[yellow]Would create directory: {current}[/yellow]")
            console.log(f"[yellow]Would create __init__.py at: {current / '__init__.py'}[/yellow]")


def _write_module(target: Path, force: bool, *, dry_run: bool = False) -> None:
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
    if target.name == "__init__.py":
        return
    if target.exists() and not force:
        raise typer.BadParameter(f"Module already exists: {target}. Use --force to overwrite.")

    if not dry_run:
        _ = target.write_text(ModuleFile().generate_content(), encoding="utf-8")
    else:
        console.log(f"[yellow]Would write module file at: {target}[/yellow]")


@app.command("create-module")
def create_module(
    ctx: ProjectContext,
    module_path: str,
    package: Annotated[
        bool, typer.Option("-p", "--package", help="Create as a package (with __init__.py)")
    ] = False,
    force: Annotated[
        bool, typer.Option("-f", "--force", help="Overwrite existing module if it exists")
    ] = False,
) -> None:
    """Create a new Python module with default logger setup.

    The path may be provided as a dotted path (e.g., "reports.new.module") or a
    filesystem path (e.g., "reports/new/module.py"). All parent packages and
    __init__.py files are created as needed.
    """
    context = ctx.obj
    _dry_run = context.dry_run

    if _dry_run:
        console.log(
            "[yellow]Dry run mode enabled. The following actions would be performed:[/yellow]"
        )

    with console.status("[bold magenta]Creating module...", spinner="dots") as _status:
        target = normalize_target(module_path, package=package)
        console.log(f"[bold green]Normalized module path to: [/bold green][u cyan]{target}[/]")
        try:
            _relative_path = target.relative_to(PACKAGE_ROOT)
        except ValueError as exc:
            raise typer.BadParameter(
                f"Module path must stay within package root: {PACKAGE_ROOT}"
            ) from exc

        _ensure_package_inits(target, dry_run=_dry_run)
        console.log(
            f"[bold green]Ensured package __init__.py files up to [/bold green][u cyan]{target.parent}[/]"
        )
        _write_module(target, force=force, dry_run=_dry_run)
        console.log(f"[bold green]Wrote module file at [/bold green][u repr.filename]{target}[/]")

    console.rule("[bold green]Module created successfully![/bold green]")


@app.command("shell")
def shell(
    module: Annotated[
        str | None,
        typer.Option(
            "-m",
            "--module",
            help="Optional dotted path to import into the shell (e.g., weldon.weldon)",
        ),
    ] = None,
    color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable rich-colored terminal output"),
    ] = True,
) -> None:
    """Start a colored IPython shell with optional module preloaded.

    - Uses Rich console for styled output
    - Imports the given module and binds it to `mod`
    - Also exposes `console` and `logger` in the shell namespace
    """
    from importlib import import_module

    ns: dict[str, object] = {"console": console, "logger": logger}
    banner = "[bold green]WeldonPackage Dev Shell[/bold green]"

    if module:
        try:
            loaded = import_module(module)
            ns["mod"] = loaded
            ns["dt"] = import_module("datetime")
            banner += f"\nImported: [cyan]{module}[/cyan] as [yellow]mod[/yellow]"
            banner += "\nImported: [cyan]datetime[/cyan] as [yellow]dt[/yellow]"
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to import module %s: %s", module, exc)
            banner += f"\n[red]Failed to import {module}: {exc}[/red]"

    # Prefer IPython for colors and better UX; fallback to code.InteractiveConsole
    try:
        from IPython.terminal.interactiveshell import TerminalInteractiveShell
        from traitlets.config import Config

        c = Config()
        c.TerminalInteractiveShell.colors = "Linux" if color else "NoColor"  # pyright: ignore[reportAny]
        c.TerminalInteractiveShell.confirm_exit = False  # pyright: ignore[reportAny]
        c.TerminalInteractiveShell.display_page = False  # pyright: ignore[reportAny]

        console.print(banner)
        sh = TerminalInteractiveShell.instance(config=c)
        sh.user_ns.update(ns)  # pyright: ignore[reportUnknownMemberType]
        sh.mainloop()
    except Exception:  # noqa: BLE001
        logger.warning("IPython not available, falling back to standard shell.", exc_info=True)
        import code

        console.print(banner)
        code.interact(local=ns)


if __name__ == "__main__":
    app()
