# Overview

- The project is an MCP (Model Context Protocol) server to access TailwindPlus components
- Implementation uses Python and FastMCP
- The project is managed using a `pyproject.toml` project file
- Python and dependencies are managed using `uv`, e.g. `uv add [package]`
- When done editing code, use `uv run ruff format .` and `uv run check . --fix` to format and check
- To run tests use: `uv run pytest`

# Architecture

The project separates domain logic from MCP wiring:

- `src/mcp_tailwindplus/tailwind_plus.py` — `TailwindPlus` class with all application logic
  (SQLite cache, data parsing, component lookup, validation, enums, dataclasses). Has no
  FastMCP dependency. Tool parameter schemas come from `Annotated` type hints on its methods.
- `src/mcp_tailwindplus/server.py` — thin factory (`create_server`) that wires `TailwindPlus`
  methods as FastMCP tools/resources with metadata (descriptions, tags, annotations).
- `src/mcp_tailwindplus/__init__.py` — entrypoint, CLI argument parsing.

This decoupling is intentional: `test_tailwind_plus.py` tests domain logic in isolation (no
MCP server, no async), while `test_server.py` tests MCP wiring via `fastmcp.Client`.

Tools are registered imperatively (`server.tool(instance.method, ...)`) rather than with
`@mcp.tool` decorators because the functions being registered are bound methods defined in a
separate module — there is no function definition to hang a `@` on. Wrapper functions would
add boilerplate and lose the `Annotated` parameter metadata.

# Project notes

- To inspect TailwindPlus data, access it: `jq '.tailwindplus' < $MCP_TAILWINDPLUS_DATA'`, the other top-level keys are metadata not TailwindPlus data


# Resources and documentation

- Model Context Protocol Specification: https://modelcontextprotocol.io/specification/latest
- FastMCP Python SDK documentation: https://gofastmcp.com/llms.txt
- Run `uv help` for assistance with `uv` to build, add/remove dependencies, etc.
