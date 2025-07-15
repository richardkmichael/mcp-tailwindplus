# MCP TailwindPlus Server - Development Guide

## Project Objective

This project is an **MCP (Model Context Protocol) server** that provides access to TailwindPlus UI components. It allows AI assistants like Claude to browse, search, and retrieve production-ready TailwindPlus components by name.

### Key Features
- **Component Discovery**: List all available TailwindPlus components
- **Smart Search**: Find components using partial name matching with dot-separated keywords
- **Component Retrieval**: Get full HTML/CSS code for specific components
- **Intelligent Error Handling**: Helpful suggestions when component names don't exist

## How It Works

### Architecture
- **FastMCP Framework**: Uses FastMCP for MCP protocol compliance
- **Python Implementation**: Built with Python 3.13+ using modern type hints
- **Component Data**: Reads from JSON file containing TailwindPlus component library
- **Package Structure**: Uses `src/` layout with `mcp_tailwindplus/` package

### Core Components

1. **TailwindPlus Class** (`src/mcp_tailwindplus/tailwind_plus.py`)
   - Main component data manager
   - Hierarchical component name parsing
   - Smart search algorithm with partial matching
   - Custom `ComponentNotFoundError` with suggestions

2. **MCP Server** (`src/mcp_tailwindplus/server.py`)
   - FastMCP server configuration
   - Tool registration and metadata
   - Exception handling (FastMCP auto-converts custom exceptions to ToolError)

3. **Data Source**
   - JSON file: `tmp/tailwindplus-components-2025-06-10-221317.json`
   - Environment variable: `MCP_TAILWINDPLUS_DATA` (optional override)
   - Hierarchical structure: `category.subcategory.component_name`

### MCP Tools Available

1. **`list_component_names`**: Get all component names
2. **`get_component_by_name`**: Retrieve specific component (with 5 suggestions on error)
3. **`search_components_by_name`**: Search with smart partial matching

### Smart Search Algorithm

The search algorithm splits search terms on dots and finds components containing ANY of the parts:
- `"application.input"` → finds components with "application" OR "input"
- `"marketing.hero"` → finds components with "marketing" OR "hero"
- Single terms work as expected: `"forms"` → finds all form components

## Development Workflow

### Setup
```bash
# Install dependencies
uv sync

# Run server
uv run mcp-tailwindplus

# Run tests
uv run pytest tests/ -v

# Format code
uv run ruff format .
uv run ruff check . --fix
```

### Testing
- **Unit tests**: `tests/test_tailwind_plus.py` (core functionality)
- **Integration tests**: `tests/test_server.py` (MCP server with FastMCP Client)
- **Error handling tests**: Comprehensive coverage for suggestions algorithm

### Key Implementation Notes

1. **FastMCP API Changes**: Updated for `CallToolResult.content` structure (not direct list)
2. **Exception Handling**: FastMCP automatically converts `ComponentNotFoundError` to `ToolError`
3. **Suggestions API**: Keyword-only `max_suggestions` parameter (`None` = unlimited)
4. **Search Unification**: Both search and error suggestions use same algorithm

## References Used

### Documentation
- **Model Context Protocol Specification**: https://modelcontextprotocol.io/specification/latest
- **FastMCP Python SDK**: https://gofastmcp.com/llms.txt
- **Python Project Layout**: src/ structure for better package organization

### Key Dependencies
- **FastMCP**: MCP server framework with tool registration
- **Python 3.13+**: Modern type hints (`int | None`, etc.)
- **pytest + pytest-asyncio**: Testing framework for async MCP operations
- **uv**: Package and dependency management

## Error Handling Design

### Custom Exceptions
- `ComponentNotFoundError`: Raised when component not found
- Includes up to 5 intelligent suggestions based on partial name matching
- FastMCP automatically converts to `ToolError` for MCP clients

### Suggestion Algorithm
```python
def _suggestions_for_component_name(name: str, *, max_suggestions: int | None = None) -> list[str]:
    # Split on dots, find components containing any part
    # Default: return all matches
    # With max_suggestions=5: limit for error messages
```

## File Structure

```
mcp-tailwindplus/
├── src/mcp_tailwindplus/
│   ├── __init__.py           # Package exports
│   ├── server.py             # FastMCP server setup
│   ├── tailwind_plus.py      # Core component logic
│   └── main.py               # Entry point
├── tests/
│   ├── test_server.py        # MCP integration tests
│   └── test_tailwind_plus.py # Unit tests
├── tmp/                      # Component data file
├── pyproject.toml           # Project configuration
└── CLAUDE.md               # Project-specific instructions
```

## Common Operations

### Add New Tool
1. Add method to `TailwindPlus` class
2. Register with `server.tool()` in `create_server()`
3. Add tests in both unit and integration test files
