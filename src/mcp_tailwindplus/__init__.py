"""MCP TailwindPlus - FastMCP server for browsing TailwindPlus components."""

import argparse
import os
import sys

__version__ = "0.1.0"

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

    args = parser.parse_args()

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


__all__ = ["__version__", "create_server", "TailwindPlus", "main"]


if __name__ == "__main__":
    main()
