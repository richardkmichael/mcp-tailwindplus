import json
import logging
from dataclasses import asdict
from enum import Enum

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP
from mcp.types import (
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

from .preview_viewer import get_preview_viewer_html
from .tailwind_plus import Framework, Mode, TailwindPlus, TailwindVersion

__all__ = ["create_server"]

logger = logging.getLogger(__name__)


def create_server(
    tailwind_plus_instance: TailwindPlus,
    version: str = "",
    project_framework: Framework | None = None,
    project_tailwind_version: TailwindVersion | None = None,
    project_mode: Mode | None = None,
) -> FastMCP:
    """Factory function to create server with TailwindPlus instance.

    The project's framework, Tailwind version and mode, when given, are offered
    first when clients complete resource template parameters.
    """

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
        description="Search TailwindPlus components by name, visible text (labels, placeholders, headings), named parts (icons, UI components, HTML elements such as nav or table, and labeled sections such as 'Mobile menu'), and category description. Returns the best matches first, each with its visible text and parts, so you can choose without retrieving the code",
        tags={"search", "components", "find"},
        annotations={
            "title": "Search Components",
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

    unaddressable_names = [
        name
        for name in tailwind_plus_instance.list_component_names()
        if name.count(".") != 3 or "/" in name
    ]
    if unaddressable_names:
        logger.warning(
            "%d component names are not product.category.subcategory.component "
            "without '/', so twplus:// resources cannot address them; tools still "
            "can: %s",
            len(unaddressable_names),
            ", ".join(unaddressable_names),
        )

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

    name_levels = ("product", "category", "subcategory", "component")

    def complete_component_argument(
        ref: PromptReference | ResourceTemplateReference,
        argument: CompletionArgument,
        context: CompletionContext | None,
    ) -> list[str] | None:
        """Complete the parameters of the component resource templates."""
        if not isinstance(ref, ResourceTemplateReference) or ref.uri not in (
            component_code_uri,
            component_preview_uri,
        ):
            return None

        chosen = (context.arguments or {}) if context else {}

        if argument.name in name_levels:
            # Each level's choices depend on the levels chosen before it.
            parent_names = name_levels[: name_levels.index(argument.name)]
            parent_levels = [chosen.get(name) for name in parent_names]
            if None in parent_levels:
                return None
            choices = tailwind_plus_instance.component_name_levels(parent_levels)
        elif argument.name == "mode":
            product = chosen.get("product")
            modes = (
                tailwind_plus_instance.modes_for_product(product)
                if product
                else list(Mode)
            )
            choices = _project_value_first([mode.value for mode in modes], project_mode)
        elif argument.name == "framework":
            choices = _project_value_first(
                [framework.value for framework in Framework], project_framework
            )
        elif argument.name == "tailwind_version":
            # Clients may preselect the first suggestion, so without a project
            # setting, offer the current version first.
            choices = _project_value_first(
                sorted((version.value for version in TailwindVersion), reverse=True),
                project_tailwind_version,
            )
        else:
            return None

        return _matching_choices(choices, argument.value)

    server.add_completion_handler(complete_component_argument)

    return server


def _project_value_first(choices: list[str], project_value: Enum | None) -> list[str]:
    """Move the project's setting to the front of the choices, so a client that
    preselects the first suggestion fills it in."""
    if project_value is None or project_value.value not in choices:
        return choices
    return [project_value.value] + [
        choice for choice in choices if choice != project_value.value
    ]


def _matching_choices(choices: list[str], typed: str) -> list[str]:
    """Return the choices matching typed text, case-insensitively: those that
    start with it first, then those that contain it elsewhere."""
    needle = typed.lower()
    starting = [choice for choice in choices if choice.lower().startswith(needle)]
    containing = [
        choice
        for choice in choices
        if needle in choice.lower() and not choice.lower().startswith(needle)
    ]
    return starting + containing
