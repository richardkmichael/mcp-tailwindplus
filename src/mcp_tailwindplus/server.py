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
        - E-commerce components (product lists, shopping carts, checkout forms, etc.)

        All components are production-ready and follow modern design patterns.
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
        tailwind_plus_instance.get_component_by_name,
        description="Retrieve the HTML/CSS code for a specific TailwindPlus component by its dotted path name",
        tags={"get", "components", "retrieve"},
        annotations={
            "title": "Get Component by Name",
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

    return server
