from fastmcp import FastMCP

from .tailwind_plus import TailwindPlus

__all__ = ["create_server"]


def create_server(tailwind_plus_instance: TailwindPlus) -> FastMCP:
    """Factory function to create server with TailwindPlus instance."""

    server = FastMCP(
        name="tailwindplus",
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

    server.tool(
        tailwind_plus_instance.get_component_preview_by_full_name,
        description="Retrieve the preview HTML for a specific TailwindPlus component by full name, framework, version, and mode",
        tags={"get", "components", "preview"},
        annotations={
            "title": "Get Component Preview by Full Name",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

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

    server.resource(
        "twplus://{component_full_name}/{framework}/{version}/{mode}",
        name="TailwindPlus Component Code",
        description="Get component code by full name, framework, version and mode",
        mime_type="application/json",
        tags={"resource", "component", "code"},
    )(tailwind_plus_instance.get_component_as_resource)

    server.resource(
        "twplus://{component_full_name}/{framework}/{version}/{mode}/preview",
        name="TailwindPlus Component Preview",
        description="Get component preview HTML by full name, framework, version and mode",
        mime_type="text/html",
        tags={"resource", "component", "preview"},
    )(tailwind_plus_instance.get_component_preview_as_resource)

    return server
