import base64
import json
import logging
from dataclasses import asdict
from enum import Enum
from importlib.metadata import metadata

from fastmcp import FastMCP
from fastmcp.apps import AppConfig, ResourceCSP
from mcp.types import (
    CompletionArgument,
    CompletionContext,
    Icon,
    PromptReference,
    ResourceTemplateReference,
)

from .preview_viewer import get_preview_viewer_html
from .tailwind_plus import Framework, Mode, TailwindPlus, TailwindVersion

__all__ = ["create_server"]

logger = logging.getLogger(__name__)

# The project's own mark, a grid of component tiles; embedded so the server
# needs no network access to show it.
_ICON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#1e293b"/>
<rect x="12" y="12" width="18" height="18" rx="4" fill="#34d399"/>
<rect x="34" y="12" width="18" height="18" rx="4" fill="#94a3b8"/>
<rect x="12" y="34" width="18" height="18" rx="4" fill="#94a3b8"/>
<rect x="34" y="34" width="18" height="18" rx="4" fill="#94a3b8"/>
</svg>"""

_ICON = Icon(
    src="data:image/svg+xml;base64," + base64.b64encode(_ICON_SVG.encode()).decode(),
    mime_type="image/svg+xml",
    sizes=["any"],
)

_INSTRUCTIONS = """\
TailwindPlus component browser - search, list, and retrieve TailwindPlus components by name.

This server provides access to a comprehensive library of TailwindPlus UI components including:
  - Marketing components (hero sections, feature sections, pricing, testimonials, etc.)
  - Application UI components (forms, navigation, data display, overlays, etc.)
  - eCommerce components (product lists, shopping carts, checkout forms, etc.)

Components are available in multiple frameworks (HTML, React, Vue), Tailwind CSS versions
(3, 4), and theme modes (light, dark, system, none).

Searching:

- search_component_names matches words in component names, visible text (labels, placeholders,
  headings), named parts (icons, UI components, HTML elements, labeled sections such as
  'Mobile menu'), and category descriptions. Each result includes the component's text, so you
  can choose a component without retrieving its code.
- Search with the words a component shows or is built from, such as 'pricing table' or
  'profile dropdown'.
- Icons are named by their shape, not their meaning: search 'exclamation triangle' for a
  warning icon.
- search_components_by_code finds the components code was copied from, by its classes and
  elements, after edits and when only part was copied. Use it to identify components already
  in a project, such as before updating them.

IMPORTANT - Mode Requirements:

- Always specify framework (html/react/vue), tailwind_version (3/4), and mode when retrieving components
- Application UI and Marketing components: use mode 'light', 'dark', or 'system'
- eCommerce components: use mode 'none' only
- Choose framework, version, and mode that match your project requirements"""


def _homepage_url() -> str | None:
    """Return the project's Homepage URL from its package metadata."""
    for project_url in metadata("mcp-tailwindplus").get_all("Project-URL") or []:
        label, _, url = project_url.partition(",")
        if label.strip() == "Homepage":
            return url.strip()
    return None


def _instructions(
    project_framework: Framework | None,
    project_tailwind_version: TailwindVersion | None,
    project_mode: Mode | None,
) -> str:
    """Return the server instructions, naming the project's settings when given."""
    settings = [
        f"{label} '{setting.value}'"
        for label, setting in (
            ("framework", project_framework),
            ("Tailwind CSS version", project_tailwind_version),
            ("mode", project_mode),
        )
        if setting is not None
    ]
    if not settings:
        return _INSTRUCTIONS
    return (
        f"{_INSTRUCTIONS}\n\n"
        f"Project settings: this project uses {', '.join(settings)}. Use them when "
        "retrieving components unless the user asks otherwise; eCommerce components "
        "still use mode 'none'."
    )


def create_server(
    tailwind_plus_instance: TailwindPlus,
    version: str = "",
    project_framework: Framework | None = None,
    project_tailwind_version: TailwindVersion | None = None,
    project_mode: Mode | None = None,
) -> FastMCP:
    """Factory function to create server with TailwindPlus instance.

    The project's framework, Tailwind version and mode, when given, are named in
    the server instructions and offered first when clients complete resource
    template parameters.
    """

    server = FastMCP(
        name="tailwindplus",
        version=version,
        website_url=_homepage_url(),
        icons=[_ICON],
        instructions=_instructions(
            project_framework, project_tailwind_version, project_mode
        ),
        # Listings and reads never change while the server runs. The TTL bounds how
        # long a client keeps results after a restart with a newer data file.
        cache_ttl=3600,
        cache_scope="public",
    )

    server.tool(
        tailwind_plus_instance.list_component_names,
        description="List TailwindPlus component names, sorted, optionally only those under a branch such as 'Application UI.Forms'. The full list is long, so prefer a branch or search_component_names",
        tags={"list", "components", "browse"},
        annotations={
            "title": "List Components",
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
        tailwind_plus_instance.search_components_by_code,
        description="Find the TailwindPlus components that code was most likely copied from, such as a component copied into a project and edited since, or part of one. Compares classes and elements regardless of order, and returns each component's closest Tailwind version and mode with a similarity from 0 to 1",
        tags={"search", "components", "code"},
        annotations={
            "title": "Search Components by Code",
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

    def warn_about_unaddressable_names() -> None:
        unaddressable_names = [
            name
            for name in tailwind_plus_instance.list_component_names()
            if name.count(".") != 3 or "/" in name
        ]
        if unaddressable_names:
            logger.warning(
                "%d component names are not product.category.subcategory.component "
                "without '/', so twplus:// resources cannot address them; tools "
                "still can: %s",
                len(unaddressable_names),
                ", ".join(unaddressable_names),
            )

    # The cache may still be building, and serving need not wait for it.
    tailwind_plus_instance.call_when_open(warn_about_unaddressable_names)

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
