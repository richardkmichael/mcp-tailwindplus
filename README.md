# TailwindPlus MCP Server

An MCP (Model Context Protocol) server for TailwindPlus UI components.

## Quick Start

1. Obtain a TailwindPlus components JSON file using the [TailwindPlus Downloader](https://github.com/richardkmichael/tailwindplus-downloader).

2. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/) for `uvx`.

3. Add to Claude Code:

`claude mcp add tailwindplus uvx -- git+https://git@github.com/richardkmichael/mcp-tailwindplus@latest --tailwindplus-data /path/to/tailwindplus-components.json`

4. Store your TailwindPlus settings in Claude's memory. This teaches Claude to use the tool and resource filters properly.

### Shared config (team)

Add with project scope and set env `MCP_TAILWINDPLUS_DATA=/path/to/tailwindplus-components.json`:

`claude mcp add tailwindplus -s project uvx -- git+https://git@github.com/richardkmichael/mcp-tailwindplus@latest`

This will allow `.mcp.json` to be commited to the repository, and but different component files can be used if necessary.

```claude
# Use TailwindPlus react for TailwindCSS v4
  ⎿  Got it.
```

## Other clients

To configure it in another MCP client:

```json
{
  "mcpServers": {
    "mcp-tailwindplus": {
      "command": "uvx",
      "args": [
        "git+https://github.com/richardkmichael/mcp-tailwindplus@latest",
        "--tailwindplus-data",
        "/path/to/tailwindplus-components.json"
      ]
    }
  }
}
```

Or, to run directly:

```bash
uvx git+https://github.com/richardkmichael/mcp-tailwindplus@latest --tailwindplus-data /path/to/tailwindplus-components.json
```

## Tips

The TailwindPlus components JSON file has a __version__.

To perform future markup maintenance easily, tell Claude to add the component __name__ and __version__ as a comment in source code.

```javascript
// Start: Application UI > Forms > Input Groups > Input with leading icon | v.2025-07-15-002529

// code

// End: Application UI > Forms > Input Groups > Input with leading icon | v.2025-07-15-002529
```

## Example usage

Ask for UI:

```claude
> I need a simple one-line search input to put in the app header.

 mcp-tailwindplus - Get Component by Full Name (MCP)(full_name: "Application UI.Forms.Input Groups.Input with leading icon", framework: "react", tailwind_version: "4")
  ⎿  {
       "version": "2025-07-14-204017",
       "full_name": "Application UI.Forms.Input Groups.Input with leading icon",
     … +15 lines (ctrl+r to expand)

 mcp-tailwindplus - Get Component by Full Name (MCP)(full_name: "Application UI.Forms.Input Groups.Input with keyboard shortcut", framework: "react", tailwind_version: "4")
  ⎿  {
       "version": "2025-07-14-204017",
       "full_name": "Application UI.Forms.Input Groups.Input with keyboard shortcut",
     … +16 lines (ctrl+r to expand)


 Perfect! Here are two ideal options for a header search input:

  1. Input with Leading Icon

  Application UI.Forms.Input Groups.Input with leading icon
  - Simple search input with magnifying glass icon
  - Just swap the EnvelopeIcon for MagnifyingGlassIcon
  - Clean, compact design perfect for headers

  2. Input with Keyboard Shortcut

  Application UI.Forms.Input Groups.Input with keyboard shortcut
  - Shows "⌘K" shortcut hint
  - Modern search UX that users expect
  - Great for power users

  For a header, I'd recommend the first one with a search icon - it's the most recognizable and space-efficient.
```

Claude appreciates other types of help too:

```
# Referring to "component" means TailwindPlus component.
  ⎿  Got it.
```

Ask for code for a use-case, help with a sketch:

```
> Show me the code for an input component we can use for a URL with the schema, e.g., `https:// [INPUT]`

⏺ I'll search for a TailwindPlus input component that would work well for URL input with a schema prefix.

⏺ mcp-tailwindplus - Search Component Names (MCP)(search_term: "input")
  ⎿  [
       "Application UI.Forms.Input Groups.Input with leading icon",
       "Application UI.Forms.Input Groups.Input with overlapping label",
     … +22 lines (ctrl+r to expand)

⏺ Perfect! Let me get the "Input with inline leading add-on" component, which would be ideal for showing a URL schema
  prefix like "https://".

⏺ mcp-tailwindplus - Get Component by Full Name (MCP)(full_name: "Application UI.Forms.Input Groups.Input with inline add-on", framework: "react", tailwind_version: "4")
  ⎿  {
       "version": "2025-07-14-204017",
       "full_name": "Application UI.Forms.Input Groups.Input with inline add-on",
     … +15 lines (ctrl+r to expand)

⏺ Here's a TailwindPlus React component for URL input with the "https://" schema prefix:

   <Claude shows React code>
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

## Running an agent in development

This project has an `.mcp.json` to run itself.

Set `MCP_TAILWINDPLUS_DATA=/path/to/file.json` prior to running your agent.

e.g.,

```
export MCP_TAILWINDPLUS_DATA=/path/to/data.json
claude
```

The data file is not specified in the MCP settings (neither via CLI argument nor env) to provide
flexibility in the local development environment.

Set the env to whatever is needed for development or testing.  A "short" (`--debug-short-test`) from
the downloader is helpful.

## Inspecting the server directly

Use the [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) to execute MCP
commands interactively, review MCP schema for Tools and Resources, etc.:

```
MCP_TAILWINDPLUS_DATA=/path/to/data.json npx @modelcontextprotocol/inspector uv run mcp-tailwindplus
```

## Data Source

Requires a TailwindPlus components JSON file.  Obtain one using the [TailwindPlus
Downloader](https://github.com/richardkmichael/tailwindplus-downloader).

Configure via:
- Command line: `--tailwindplus-data /path/to/data.json`
- Environment: `MCP_TAILWINDPLUS_DATA=/path/to/data.json`
