import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_tailwindplus.server import create_server
from mcp_tailwindplus.tailwind_plus import TailwindPlus


@pytest.fixture
def sample_mcp_data():
    """Sample TailwindPlus data for MCP testing with new format."""
    return {
        "version": "test-server-2025-07-15",
        "downloaded_at": "2025-07-15T00:00:00.000Z",
        "component_count": 4,
        "download_duration": "1.0s",
        "downloader_version": "3.0.0",
        "tailwindplus": {
            "Application UI": {
                "Forms": {
                    "Input Groups": {
                        "With icon": {
                            "name": "With icon",
                            "snippets": [
                                {
                                    "code": '<input class="form-input" type="text">',
                                    "language": "html",
                                    "mode": "light",
                                    "name": "html",
                                    "preview": "<div>Input with icon preview</div>",
                                    "supportsDarkMode": False,
                                    "version": 4,
                                }
                            ],
                        }
                    },
                    "Select Menus": {
                        "Basic": {
                            "name": "Basic",
                            "snippets": [
                                {
                                    "code": '<select class="form-select"></select>',
                                    "language": "html",
                                    "mode": "light",
                                    "name": "html",
                                    "preview": "<div>Basic select preview</div>",
                                    "supportsDarkMode": True,
                                    "version": 4,
                                }
                            ],
                        }
                    },
                },
                "Navigation": {
                    "Breadcrumbs": {
                        "Simple": {
                            "name": "Simple",
                            "snippets": [
                                {
                                    "code": '<nav aria-label="Breadcrumb"></nav>',
                                    "language": "html",
                                    "mode": "light",
                                    "name": "html",
                                    "preview": "<nav>Simple breadcrumb preview</nav>",
                                    "supportsDarkMode": True,
                                    "version": 4,
                                },
                                {
                                    "code": '<nav aria-label="Breadcrumb" class="dark"></nav>',
                                    "language": "html",
                                    "mode": "dark",
                                    "name": "html",
                                    "preview": "<nav>Simple breadcrumb preview</nav>",
                                    "supportsDarkMode": True,
                                    "version": 4,
                                },
                                {
                                    "code": '<nav aria-label="Breadcrumb" class="system"></nav>',
                                    "language": "html",
                                    "mode": "system",
                                    "name": "html",
                                    "preview": "<nav>Simple breadcrumb preview</nav>",
                                    "supportsDarkMode": True,
                                    "version": 4,
                                },
                            ],
                        }
                    }
                },
            },
            "Marketing": {
                "Hero Sections": {
                    "Centered": {
                        "name": "Centered",
                        "snippets": [
                            {
                                "code": '<section class="hero"></section>',
                                "language": "html",
                                "mode": "light",
                                "name": "html",
                                "preview": "<section>Centered hero preview</section>",
                                "supportsDarkMode": False,
                                "version": 4,
                            }
                        ],
                    }
                }
            },
        },
    }


@pytest.fixture
def data_file(sample_mcp_data, tmp_path):
    """Write sample MCP data to a temp file and return its path."""
    path = tmp_path / "test-server-data.json"
    path.write_text(json.dumps(sample_mcp_data))
    return str(path)


@pytest.fixture
def mcp_server(data_file, tmp_path):
    """Create server with test data from temp file."""
    test_tailwind_plus = TailwindPlus(data_file, cache_dir=str(tmp_path))
    yield create_server(test_tailwind_plus, version="0.0.0-test")
    test_tailwind_plus.close()


class TestMCPServerFunctionality:
    """Test FastMCP server functionality using proper FastMCP testing patterns."""

    @pytest.mark.asyncio
    async def test_list_all_component_names(self, mcp_server):
        """Test the list_component_names tool."""
        async with Client(mcp_server) as client:
            result = await client.call_tool("list_component_names", {})

            assert len(result.content) == 1
            assert result.content[0].text is not None

            # The result comes back as JSON string from FastMCP Client
            component_names = json.loads(result.content[0].text)
            assert isinstance(component_names, list)
            assert len(component_names) == 4

            expected_names = [
                "Application UI.Forms.Input Groups.With icon",
                "Application UI.Forms.Select Menus.Basic",
                "Application UI.Navigation.Breadcrumbs.Simple",
                "Marketing.Hero Sections.Centered",
            ]
            assert sorted(component_names) == sorted(expected_names)

    @pytest.mark.asyncio
    async def test_get_component_by_full_name_exists(self, mcp_server):
        """Test getting an existing component."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "get_component_by_full_name",
                {
                    "full_name": "Application UI.Forms.Input Groups.With icon",
                    "framework": "html",
                    "tailwind_version": "4",
                    "mode": "light",
                },
            )

            assert len(result.content) == 1
            assert result.content[0].text is not None

            # Parse the JSON result
            component_data = json.loads(result.content[0].text)
            assert isinstance(component_data, dict)
            assert (
                component_data["full_name"]
                == "Application UI.Forms.Input Groups.With icon"
            )
            assert component_data["name"] == "With icon"
            assert component_data["version"] == "test-server-2025-07-15"
            assert component_data["framework"] == "html"
            assert component_data["language"] == "html"
            assert component_data["tailwind_version"] == "4"
            assert isinstance(component_data["code"], str)
            assert "form-input" in component_data["code"]

    @pytest.mark.asyncio
    async def test_get_component_by_full_name_not_exists(self, mcp_server):
        """Test getting a non-existent component."""
        async with Client(mcp_server) as client:
            # Should raise ToolError for non-existent component (converted from ComponentNotFoundError)
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool(
                    "get_component_by_full_name",
                    {
                        "full_name": "nonexistent.component",
                        "framework": "html",
                        "tailwind_version": "4",
                        "mode": "light",
                    },
                )

            # Verify the error message contains helpful information
            error_message = str(exc_info.value)
            assert "nonexistent.component" in error_message
            assert "not found" in error_message.lower()

    @pytest.mark.asyncio
    async def test_get_component_by_full_name_with_suggestions(self, mcp_server):
        """Test that error includes suggestions for similar component names."""
        async with Client(mcp_server) as client:
            # Try a name that should generate suggestions
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool(
                    "get_component_by_full_name",
                    {
                        "full_name": "Application.Forms.Wrong",
                        "framework": "html",
                        "tailwind_version": "4",
                        "mode": "light",
                    },
                )

            # Verify suggestions are included in the ToolError message
            error_message = str(exc_info.value)
            assert "Application.Forms.Wrong" in error_message
            assert "not found" in error_message.lower()
            # Should contain suggestions since "application" and "forms" are valid parts
            assert (
                "did you mean" in error_message.lower() or len(error_message) > 50
            )  # Has suggestions

    @pytest.mark.asyncio
    async def test_search_component_names(self, mcp_server):
        """Test searching for component names."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "search_component_names", {"search_term": "Forms"}
            )

            assert len(result.content) == 1
            assert result.content[0].text is not None

            # Parse the JSON result
            search_results = json.loads(result.content[0].text)
            assert isinstance(search_results, list)
            assert len(search_results) == 2

            expected_results = [
                "Application UI.Forms.Input Groups.With icon",
                "Application UI.Forms.Select Menus.Basic",
            ]
            assert sorted(search_results) == sorted(expected_results)

    @pytest.mark.asyncio
    async def test_search_components_case_insensitive(self, mcp_server):
        """Test case insensitive search."""
        async with Client(mcp_server) as client:
            # Test lowercase
            result_lower = await client.call_tool(
                "search_component_names", {"search_term": "hero"}
            )

            # Test uppercase
            result_upper = await client.call_tool(
                "search_component_names", {"search_term": "HERO"}
            )

            assert len(result_lower.content) == 1
            assert len(result_upper.content) == 1

            # The results come back as JSON strings from FastMCP Client
            # For single results, FastMCP might return the item directly instead of a list
            lower_text = result_lower.content[0].text
            upper_text = result_upper.content[0].text

            # Try to parse as JSON, if it fails it might be a single string
            try:
                lower_results = json.loads(lower_text)
            except json.JSONDecodeError:
                # Single result returned as plain string, wrap in list
                lower_results = [lower_text]

            try:
                upper_results = json.loads(upper_text)
            except json.JSONDecodeError:
                # Single result returned as plain string, wrap in list
                upper_results = [upper_text]

            assert lower_results == upper_results
            assert isinstance(lower_results, list)
            assert len(lower_results) == 1
            assert "Marketing.Hero Sections.Centered" in lower_results

    @pytest.mark.asyncio
    async def test_search_components_no_matches(self, mcp_server):
        """Test search with no matches."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "search_component_names", {"search_term": "nonexistent"}
            )

            # Handle empty results - might return no content or empty list
            if len(result.content) == 0:
                search_results = []
            else:
                search_results = json.loads(result.content[0].text)

            assert isinstance(search_results, list)
            assert len(search_results) == 0


class TestMCPServerMetadata:
    """Test FastMCP server metadata and configuration."""

    def test_server_name_and_instructions(self, mcp_server):
        """Test server name and instructions."""
        assert mcp_server.name == "tailwindplus"
        assert "component browser" in mcp_server.instructions.lower()

    @pytest.mark.asyncio
    async def test_server_tools_exist(self, mcp_server):
        """Test that all expected tools are registered."""
        tools = await mcp_server.list_tools()
        tool_names = [t.name for t in tools]

        expected_tools = [
            "list_component_names",
            "get_component_by_full_name",
            "get_component_preview_by_full_name",
            "search_component_names",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names

    @pytest.mark.asyncio
    async def test_tool_metadata(self, mcp_server):
        """Test tool metadata and annotations."""
        tools = await mcp_server.list_tools()
        tools_by_name = {t.name: t for t in tools}

        # Test list tool
        list_tool = tools_by_name["list_component_names"]
        assert (
            list_tool.description
            == "Get a complete list of all available TailwindPlus component names organized by category"
        )
        assert "list" in list_tool.tags
        assert "components" in list_tool.tags
        assert list_tool.annotations.readOnlyHint is True
        assert list_tool.annotations.idempotentHint is True

        # Test get tool
        get_tool = tools_by_name["get_component_by_full_name"]
        assert (
            get_tool.description
            == "Retrieve component code (HTML/React/Vue) for a specific TailwindPlus component by full name, framework, version, and mode"
        )
        assert "get" in get_tool.tags
        assert "components" in get_tool.tags

        # Test search tool
        search_tool = tools_by_name["search_component_names"]
        assert (
            search_tool.description
            == "Search for TailwindPlus component names by pattern or keyword (case-insensitive)"
        )
        assert "search" in search_tool.tags
        assert "components" in search_tool.tags


class TestMCPAppsPreviewViewer:
    """Test MCP Apps preview viewer configuration."""

    @pytest.mark.asyncio
    async def test_preview_viewer_resource_exists(self, mcp_server):
        """Test that the ui:// preview viewer resource is registered."""
        resources = await mcp_server.list_resources()
        resource_uris = [str(r.uri) for r in resources]
        assert "ui://tailwindplus/preview-viewer" in resource_uris

    @pytest.mark.asyncio
    async def test_preview_viewer_mime_type(self, mcp_server):
        """Test that the preview viewer uses the MCP Apps MIME type, not plain text/html."""
        resources = await mcp_server.list_resources()
        viewer = next(
            r for r in resources if str(r.uri) == "ui://tailwindplus/preview-viewer"
        )
        assert viewer.mime_type == "text/html;profile=mcp-app"

    @pytest.mark.asyncio
    async def test_preview_viewer_html_content(self, mcp_server):
        """Test that the preview viewer returns valid HTML with the ext-apps SDK."""
        result = await mcp_server.read_resource("ui://tailwindplus/preview-viewer")
        html = result.contents[0].content
        assert "ontoolresult" in html
        assert "ext-apps" in html
        assert "preview-container" in html
        assert "tw-component-css" in html

    @pytest.mark.asyncio
    async def test_preview_tool_has_app_config(self, mcp_server):
        """Test that the preview tool declares an app resource URI."""
        tools = await mcp_server.list_tools()
        preview_tool = next(
            t for t in tools if t.name == "get_component_preview_by_full_name"
        )
        tool_meta = preview_tool.meta or {}
        ui_meta = tool_meta.get("ui", tool_meta.get("fastmcp", {}).get("ui", {}))
        assert ui_meta.get("resourceUri") == "ui://tailwindplus/preview-viewer"

    @pytest.mark.asyncio
    async def test_twplus_preview_resource_uses_text_html(self, mcp_server):
        """Test that the twplus:// preview resource uses text/html, not the MCP Apps MIME type."""
        templates = await mcp_server.list_resource_templates()
        preview_template = next(
            t
            for t in templates
            if "preview" in str(t.uri_template)
            and str(t.uri_template).startswith("twplus://")
        )
        assert preview_template.mime_type == "text/html"


class TestMCPServerIntegration:
    """Test end-to-end server functionality."""

    @pytest.mark.asyncio
    async def test_tool_integration(self, mcp_server):
        """Test that tools work together correctly."""
        async with Client(mcp_server) as client:
            # First, get all component names
            list_result = await client.call_tool("list_component_names", {})
            assert len(list_result.content) == 1

            all_names = json.loads(list_result.content[0].text)

            # Then try to get each component
            for name in all_names:
                get_result = await client.call_tool(
                    "get_component_by_full_name",
                    {
                        "full_name": name,
                        "framework": "html",
                        "tailwind_version": "4",
                        "mode": "none" if name.startswith("Ecommerce") else "light",
                    },
                )
                assert len(get_result.content) == 1

                component_data = json.loads(get_result.content[0].text)
                assert component_data["full_name"] == name
                assert component_data["code"] != ""

    @pytest.mark.asyncio
    async def test_search_returns_valid_components(self, mcp_server):
        """Test that search results can be retrieved."""
        async with Client(mcp_server) as client:
            # Search for components
            search_result = await client.call_tool(
                "search_component_names", {"search_term": "Application UI"}
            )
            assert len(search_result.content) == 1

            search_names = json.loads(search_result.content[0].text)

            # Verify each search result can be retrieved
            for name in search_names:
                get_result = await client.call_tool(
                    "get_component_by_full_name",
                    {
                        "full_name": name,
                        "framework": "html",
                        "tailwind_version": "4",
                        "mode": "none" if name.startswith("Ecommerce") else "light",
                    },
                )
                assert len(get_result.content) == 1

                component_data = json.loads(get_result.content[0].text)
                assert component_data["full_name"] == name

                # Verify component has expected structure
                assert isinstance(component_data["code"], str)
                assert len(component_data["code"]) > 0
                assert component_data["version"] == "test-server-2025-07-15"
                assert component_data["name"] is not None
