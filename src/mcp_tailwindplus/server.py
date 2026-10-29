import json
from dataclasses import asdict

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP

from .tailwind_plus import (
    Framework,
    Mode,
    TailwindPlus,
    TailwindVersion,
    get_preview_viewer_html,
)

__all__ = ["create_server"]


def create_server(tailwind_plus_instance: TailwindPlus, version: str = "") -> FastMCP:
    """Factory function to create server with TailwindPlus instance."""

    server = FastMCP(
        name="tailwindplus",
        version=version,
        instructions="""TailwindPlus component browser - search, list, and retrieve TailwindPlus components by name.

        This server provides access to a comprehensive library of TailwindPlus UI components including:
          - Marketing components (hero sections, feature sections, pricing, testimonials, etc.)
          - Application UI components (forms, navigation, data display, overlays, etc.)
          - eCommerce components (product lists, shopping carts, checkout forms, etc.)

        Components are available in multiple frameworks (HTML, React, Vue), Tailwind CSS versions
        (3, 4), and theme modes (light, dark, system, none).

        IMPORTANT - Mode Requirements:

        - Always specify framework (html/react/vue), tailwind_version (3/4), and mode when retrieving components
        - Application UI and Marketing components: use mode 'light', 'dark', or 'system'
        - eCommerce components: use mode 'none' only
        - Choose framework, version, and mode that match your project requirements
        """,
        # Listings and reads never change while the server runs. The TTL bounds how
        # long a client keeps results after a restart with a newer data file.
        cache_ttl=3600,
        cache_scope="public",
    )

    server.tool(
        tailwind_plus_instance.list_component_names,
        description="Get a complete list of all available TailwindPlus component names organized by category",
        tags={"list", "components", "browse"},
        annotations={
            "title": "List All Components",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    server.tool(
        tailwind_plus_instance.get_component_by_full_name,
        description="Retrieve component code (HTML/React/Vue) for a specific TailwindPlus component by full name, framework, version, and mode",
        tags={"get", "components", "retrieve"},
        annotations={
            "title": "Get Component by Full Name",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    preview_viewer_uri = "ui://tailwindplus/preview-viewer"

    server.tool(
        tailwind_plus_instance.get_component_preview_by_full_name,
        description="Retrieve the preview HTML for a specific TailwindPlus component by full name, framework, version, and mode",
        tags={"get", "components", "preview"},
        annotations={
            "title": "Get Component Preview by Full Name",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
        app=AppConfig(resource_uri=preview_viewer_uri),
    )

    server.resource(
        preview_viewer_uri,
        name="TailwindPlus Preview Viewer",
        description="MCP Apps viewer for rendering TailwindPlus component previews",
        tags={"app", "preview", "viewer"},
        app=AppConfig(
            csp=ResourceCSP(
                resource_domains=[
                    "https://rsms.me",
                    "https://cdn.jsdelivr.net",
                    "https://tailwindcss.com",
                    "https://unpkg.com",
                    "https://images.unsplash.com",
                ],
            ),
        ),
    )(get_preview_viewer_html)

    server.tool(
        tailwind_plus_instance.search_component_names,
        description="Search for TailwindPlus component names by pattern or keyword (case-insensitive)",
        tags={"search", "components", "find"},
        annotations={
            "title": "Search Component Names",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    server.tool(
        tailwind_plus_instance.list_tailwindplus_information,
        description="Get TailwindPlus metadata information including version, download date, component count, etc.",
        tags={"info", "metadata", "version"},
        annotations={
            "title": "List TailwindPlus Information",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    # Each level of a component's dotted name is its own URI path segment, so
    # clients can complete the name one level at a time.
    component_code_uri = (
        "twplus://components/{product}/{category}/{subcategory}/{component}"
        "/{framework}/{tailwind_version}/{mode}"
    )
    component_preview_uri = f"{component_code_uri}/preview"

    def read_component_code(
        product: str,
        category: str,
        subcategory: str,
        component: str,
        framework: str,
        tailwind_version: str,
        mode: str,
    ) -> str:
        """Return a component's code and metadata as JSON."""
        found = tailwind_plus_instance.get_component_by_full_name(
            ".".join((product, category, subcategory, component)),
            Framework(framework),
            TailwindVersion(tailwind_version),
            Mode(mode),
        )
        return json.dumps(asdict(found), default=lambda enum: enum.value)

    def read_component_preview(
        product: str,
        category: str,
        subcategory: str,
        component: str,
        framework: str,
        tailwind_version: str,
        mode: str,
    ) -> str:
        """Return a component's preview HTML."""
        return tailwind_plus_instance.get_component_preview_by_full_name(
            ".".join((product, category, subcategory, component)),
            Framework(framework),
            TailwindVersion(tailwind_version),
            Mode(mode),
        )

    server.resource(
        component_code_uri,
        name="TailwindPlus Component Code",
        description="Get component code as JSON",
        mime_type="application/json",
        tags={"resource", "component", "code"},
    )(read_component_code)

    server.resource(
        component_preview_uri,
        name="TailwindPlus Component Preview",
        description="Get component preview HTML",
        mime_type="text/html",
        tags={"resource", "component", "preview"},
    )(read_component_preview)

    return server
