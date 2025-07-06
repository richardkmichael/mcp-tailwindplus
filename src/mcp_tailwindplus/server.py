from fastmcp import FastMCP

from . import __version__
from .tailwind_plus import TailwindPlus

__all__ = ["create_server"]


def create_server(tailwind_plus_instance: TailwindPlus = None) -> FastMCP:
    """Factory function to create server with TailwindPlus instance."""
    if tailwind_plus_instance is None:
        tailwind_plus_instance = TailwindPlus()

    server = FastMCP(
        name="tailwindplus",
        title="TailwindPlus Component Browser",
        version=__version__,
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
        tags={"list", "components", "browse"},
        annotations={
            "title": "List All Components",
            "description": "Get a complete list of all available TailwindPlus component names organized by category",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    server.tool(
        tailwind_plus_instance.get_component_by_name,
        tags={"get", "components", "retrieve"},
        annotations={
            "title": "Get Component by Name",
            "description": "Retrieve the HTML/CSS code for a specific TailwindPlus component by its dotted path name",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    server.tool(
        tailwind_plus_instance.search_components_by_name,
        tags={"search", "components", "find"},
        annotations={
            "title": "Search Components",
            "description": "Search for TailwindPlus components by name pattern or keyword (case-insensitive)",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    return server
