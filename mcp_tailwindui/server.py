from fastmcp import FastMCP
from .tailwind_plus import TailwindPlus

__all__ = ["create_server"]


def create_server(tailwind_plus_instance: TailwindPlus = None) -> FastMCP:
    """Factory function to create server with TailwindPlus instance."""
    if tailwind_plus_instance is None:
        tailwind_plus_instance = TailwindPlus()

    server = FastMCP(
        name="tailwindui",
        instructions="TailwindPlus component browser - search, list, and retrieve TailwindUI components by name",
    )

    server.tool(
        tailwind_plus_instance.list_component_names,
        tags={"list", "components"},
        annotations={
            "title": "List All Components",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    server.tool(
        tailwind_plus_instance.get_component_by_name,
        tags={"get", "components"},
        annotations={
            "title": "Get Component by Name",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    server.tool(
        tailwind_plus_instance.search_components_by_name,
        tags={"search", "components"},
        annotations={
            "title": "Search Components",
            "readOnlyHint": True,
            "idempotentHint": True,
        },
    )

    return server
