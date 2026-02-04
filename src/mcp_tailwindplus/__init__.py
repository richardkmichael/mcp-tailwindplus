"""MCP TailwindPlus - FastMCP server for browsing TailwindPlus components."""

import argparse
import glob
import os
import sys
from importlib.metadata import version

__version__ = version("mcp-tailwindplus")

from .server import create_server
from .tailwind_plus import TailwindPlus


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
        "--clear-cache",
        action="store_true",
        help="Remove all cached component databases and exit",
    )

    args = parser.parse_args()

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

    try:
        tailwind_plus = TailwindPlus(data_file)
        mcp_server = create_server(tailwind_plus)
        mcp_server.run()

    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


def _clear_cache():
    """Remove all cached component databases."""
    from platformdirs import user_cache_dir

    cache_dir = user_cache_dir("mcp-tailwindplus")
    pattern = os.path.join(cache_dir, "tailwindplus_components_cache_*.db")
    files = glob.glob(pattern)

    if not files:
        print(f"No cache files found in {cache_dir}")
        return

    for f in files:
        os.remove(f)
        print(f"Removed: {f}")

    print(f"\nCleared {len(files)} cache file(s)")


__all__ = ["__version__", "create_server", "TailwindPlus", "main"]


if __name__ == "__main__":
    main()
