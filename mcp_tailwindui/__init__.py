"""MCP TailwindUI - FastMCP server for browsing TailwindUI components."""

from .server import create_server
from .tailwind_plus import TailwindPlus

__version__ = "0.1.0"
__all__ = ["create_server", "TailwindPlus"]
