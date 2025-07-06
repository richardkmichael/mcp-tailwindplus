"""MCP TailwindPlus - FastMCP server for browsing TailwindPlus components."""

import sys

__version__ = "0.1.0"

from .server import create_server
from .tailwind_plus import TailwindPlus


def main():
    """Main entry point - start the MCP TailwindPlus server."""
    try:
        # Create the server
        mcp_server = create_server()

        # Run the server
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
