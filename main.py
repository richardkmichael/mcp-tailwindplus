"""Main entry point for MCP TailwindUI server."""

import sys
from mcp_tailwindui import create_server


def main():
    """Start the MCP TailwindUI server."""
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


if __name__ == "__main__":
    main()
