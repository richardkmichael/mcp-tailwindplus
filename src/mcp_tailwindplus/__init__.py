"""MCP TailwindPlus - FastMCP server for browsing TailwindPlus components."""

import argparse
import glob
import logging
import os
import sys
from enum import Enum
from importlib.metadata import version

__version__ = version("mcp-tailwindplus")

from platformdirs import user_cache_dir

from .tailwind_plus import Framework, Mode, TailwindPlus, TailwindVersion

logger = logging.getLogger(__name__)

FRAMEWORK_CHOICES = [framework.value for framework in Framework]
TAILWIND_VERSION_CHOICES = [version.value for version in TailwindVersion]
# 'none' is not a project choice: it is the only mode of eCommerce components.
MODE_CHOICES = [mode.value for mode in Mode if mode is not Mode.NONE]


def main():
    """Main entry point - start the MCP TailwindPlus server."""
    parser = argparse.ArgumentParser(
        description="MCP TailwindPlus - FastMCP server for browsing TailwindPlus components",
        epilog="If --tailwindplus-data is not provided, the MCP_TAILWINDPLUS_DATA environment variable will be used.",
    )
    parser.add_argument(
        "--tailwindplus-data",
        metavar="PATH",
        help="Path to TailwindPlus components JSON data file",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP server bind address (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP server port (default: 8000)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Remove all cached component databases and exit",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging and print tracebacks on startup errors",
    )
    parser.add_argument(
        "--framework",
        choices=FRAMEWORK_CHOICES,
        help="Project's framework, offered first when completing resource URIs "
        "(default: MCP_TAILWINDPLUS_FRAMEWORK)",
    )
    parser.add_argument(
        "--tailwind-version",
        choices=TAILWIND_VERSION_CHOICES,
        help="Project's Tailwind CSS version, offered first when completing "
        "resource URIs (default: MCP_TAILWINDPLUS_TAILWIND_VERSION)",
    )
    parser.add_argument(
        "--mode",
        choices=MODE_CHOICES,
        help="Project's theme mode, offered first when completing resource URIs "
        "for Application UI and Marketing components (default: MCP_TAILWINDPLUS_MODE)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.clear_cache:
        _clear_cache()
        sys.exit(0)

    # Determine data file path: command line > environment > error
    data_file = args.tailwindplus_data or os.environ.get("MCP_TAILWINDPLUS_DATA")

    if not data_file:
        parser.error(
            "No TailwindPlus data file specified.\n\n"
            "Please provide the data file path using either:\n"
            "  --tailwindplus-data /path/to/data.json\n"
            "  MCP_TAILWINDPLUS_DATA=/path/to/data.json"
        )

    if not os.path.exists(data_file):
        parser.error(f"TailwindPlus data file not found: {data_file}")

    project_framework = _project_setting(
        parser,
        args.framework,
        "MCP_TAILWINDPLUS_FRAMEWORK",
        Framework,
        FRAMEWORK_CHOICES,
    )
    project_tailwind_version = _project_setting(
        parser,
        args.tailwind_version,
        "MCP_TAILWINDPLUS_TAILWIND_VERSION",
        TailwindVersion,
        TAILWIND_VERSION_CHOICES,
    )
    project_mode = _project_setting(
        parser, args.mode, "MCP_TAILWINDPLUS_MODE", Mode, MODE_CHOICES
    )

    from .server import create_server

    try:
        with TailwindPlus(data_file) as tailwind_plus:
            mcp_server = create_server(
                tailwind_plus,
                version=__version__,
                project_framework=project_framework,
                project_tailwind_version=project_tailwind_version,
                project_mode=project_mode,
            )

            # FastMCP's banner checks PyPI for a newer FastMCP before serving,
            # which delays every start by up to 2 s when PyPI is unreachable.
            if args.transport == "http":
                mcp_server.run(
                    transport="http",
                    host=args.host,
                    port=args.port,
                    show_banner=False,
                )
            else:
                mcp_server.run(show_banner=False)

    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        if args.debug:
            logger.exception("Error starting server")
        else:
            print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


def _project_setting[SettingT: Enum](
    parser: argparse.ArgumentParser,
    cli_value: str | None,
    env_name: str,
    setting_type: type[SettingT],
    choices: list[str],
) -> SettingT | None:
    """Return a project setting from the command line, else the environment."""
    value = cli_value or os.environ.get(env_name)
    if value is None:
        return None
    if value not in choices:
        parser.error(f"{env_name} must be one of {', '.join(choices)}; got {value!r}")
    return setting_type(value)


def _clear_cache():
    """Remove all cached component databases, with their lock files and the
    partial files of interrupted builds."""
    cache_dir = user_cache_dir("mcp-tailwindplus")
    pattern = os.path.join(cache_dir, "tailwindplus_components_cache_*")
    files = glob.glob(pattern)

    if not files:
        print(f"No cache files found in {cache_dir}")
        return

    for f in files:
        os.remove(f)
        print(f"Removed: {f}")

    print(f"\nCleared {len(files)} cache file(s)")


def __getattr__(name: str):
    # The server module imports FastMCP, which takes most of a second. Importing
    # it on first use keeps the package light for the worker processes that
    # parse component code while the cache is built.
    if name == "create_server":
        from .server import create_server

        return create_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["__version__", "create_server", "TailwindPlus", "main"]


if __name__ == "__main__":
    main()
