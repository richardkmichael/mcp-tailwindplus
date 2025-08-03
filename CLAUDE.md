# Overview

- The project is an MCP (Model Context Protocol) server to access TailwindPlus components
- Implementation uses Python and FastMCP
- The project is managed using a `pyproject.toml` project file
- Python and dependencies are managed using `uv`, e.g. `uv add [package]`
- When done editing code, use `uv run ruff format .` and `uv run check . --fix` to format and check

# Project notes

- This project does not use FastMCP's decorator methods
- Main entrypoint is `src/mcp_tailwindplus/__init__.py`
- FastMCP MCP server is created in `src/mcp_tailwindplus/server.py`
- Functionality is provided by the class in `src/mcp_tailwindplus/tailwind_plus.py`; wrapped by the server

# Resources and documentation

- Model Context Protocol Specification: https://modelcontextprotocol.io/specification/latest
- FastMCP Python SDK documentation: https://gofastmcp.com/llms.txt
- Run `uv help` for assistance with `uv` to build, add/remove dependencies, etc.
