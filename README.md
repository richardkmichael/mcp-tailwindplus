# MCP TailwindPlus Server

An MCP (Model Context Protocol) server that provides access to TailwindPlus UI components. Browse, search, and retrieve production-ready components in HTML, React, and Vue frameworks.

## Quick Start

Obtain a TailwindPlus components JSON file using the [TailwindPlus Downloader](https://github.com/richardkmichael/tailwindplus-downloader).

Install and run via [`uvx`](https://docs.astral.sh/uv/getting-started/installation/), or see Development below:

```bash
uvx --from git+https://github.com/richardkmichael/mcp-tailwindplus@latest mcp-tailwindplus --tailwindplus-data /path/to/tailwindplus-components.json
```

To configure it in your MCP client:

```json
{
  "mcpServers": {
    "mcp-tailwindplus": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/richardkmichael/mcp-tailwindplus@latest",
        "mcp-tailwindplus",
        "--tailwindplus-data",
        "/path/to/tailwindplus-components.json"
      ]
    }
  }
}
```

### Environment Variables

- `MCP_TAILWINDPLUS_DATA`: Path to TailwindPlus component data file (alternative to `--tailwindplus-data`)

## Available Tools

1. `list_component_names` - List all available components
2. `get_component_by_full_name` - Get component code (HTML/React/Vue)
3. `get_component_preview_by_full_name` - Get component preview HTML
4. `search_component_names` - Search components by keyword

## Available Resources

MCP resources provide direct URI access to components:

- `Component Code`: `twplus://{component_full_name}/{framework}/{version}`
- `Component Preview`: `twplus://{component_full_name}/{framework}/{version}/preview`

⚠️ **Note**: Resources require MCP clients that support "resource templates". Not all clients support this feature.

### Parameters

- `framework`: `html`, `react`, or `vue`
- `version`: `3` or `4` (Tailwind CSS version)
- `component_full_name`: Dot-separated path (e.g., `Application UI.Forms.Input Groups.Label with leading icon`)

## Component Organization

Components are organized hierarchically:
- Categories: Marketing, Application UI, E-commerce, etc.
- Full Names: Use dot-separated paths like `Marketing.Hero Sections.Simple centered`
- Search: Supports partial matching with keywords

## Development

```bash
# Setup
uv sync

# Run server
uv run mcp-tailwindplus --tailwindplus-data /path/to/data.json

# Test
uv run pytest tests/ -v

# Format
uv run ruff format .
uv run ruff check . --fix
```

## Data Source

Requires a JSON file containing TailwindPlus component library data.  Obtain one using the
[TailwindPlus Downloader](https://github.com/richardkmichael/tailwindplus-downloader).

Configure via:
- Command line: `--tailwindplus-data /path/to/data.json`
- Environment: `MCP_TAILWINDPLUS_DATA=/path/to/data.json`
