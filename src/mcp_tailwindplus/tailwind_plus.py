import json
import os
from dataclasses import dataclass
from typing import Annotated, TextIO


@dataclass
class Component:
    version: str
    name: str
    short_name: str
    html: str


class ComponentNotFoundError(Exception):
    """Raised when a component is not found by its name."""

    def __init__(self, component_name: str, suggestions: list[str] | None = None):
        self.component_name = component_name
        self.suggestions = suggestions or []

        # Create a helpful error message
        message = f"Component '{component_name}' not found."

        if self.suggestions:
            message += f" Did you mean one of: {', '.join(self.suggestions)}?"

        super().__init__(message)


class TailwindPlus:
    def __init__(self, data_source: str | TextIO | None = None):
        if data_source is None:
            # Use default file path
            data_source = (
                os.environ.get("MCP_TAILWINDPLUS_DATA")
                or "tmp/tailwindplus-components-2025-06-10-221317.json"
            )

        # Store the data source path for version extraction
        self._data_source_path = data_source if isinstance(data_source, str) else None

        if isinstance(data_source, str):
            # It's a file path
            with open(data_source) as f:
                raw_data = json.load(f)
        else:
            # It's a file-like object (StringIO, etc.)
            raw_data = json.load(data_source)

        # Extract version from filename and flatten to components
        self.version = self._extract_version()
        self._components_by_name = self._flatten_to_components(raw_data)

    def _extract_version(self) -> str:
        """Extract version from filename like 'tailwindplus-components-2025-06-10-221317.json'."""
        if not self._data_source_path:
            return "test"  # Default version for tests or StringIO usage

        filename = os.path.basename(self._data_source_path)
        # Extract the part between 'tailwindplus-components-' and '.json'
        if filename.startswith("tailwindplus-components-") and filename.endswith(
            ".json"
        ):
            return filename[len("tailwindplus-components-") : -len(".json")]

        raise ValueError(f"Cannot determine version from filename: {filename}")

    def _flatten_to_components(
        self, obj: dict, prefix: str = ""
    ) -> dict[str, Component]:
        """Transform JSON tree to flat dict of Component objects in a single pass."""
        components = {}

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = ".".join([prefix, key]) if prefix else key

                if isinstance(value, str):
                    # This is a component (HTML string) - current_path is already the full path
                    components[current_path] = Component(
                        version=self.version,
                        name=current_path,
                        short_name=key,
                        html=value,
                    )
                elif isinstance(value, dict):
                    # Check if this dict contains only string values (components)
                    if all(isinstance(v, str) for v in value.values()):
                        # All values are HTML strings, so each key is a component
                        for comp_key, comp_html in value.items():
                            comp_path = ".".join([current_path, comp_key])
                            components[comp_path] = Component(
                                version=self.version,
                                name=comp_path,
                                short_name=comp_key,
                                html=comp_html,
                            )
                    else:
                        # Mixed content, recurse deeper
                        components.update(
                            self._flatten_to_components(value, current_path)
                        )

        return components

    def _suggestions_for_component_name(
        self, name: str, *, max_suggestions: int | None = None
    ) -> list[str]:
        """Generate component name suggestions based on partial matches."""
        name_parts = [part.lower() for part in name.lower().split(".")]

        suggestions = [
            comp_name
            for comp_name in self._components_by_name.keys()
            if any(part in comp_name.lower() for part in name_parts)
        ]

        return suggestions if max_suggestions is None else suggestions[:max_suggestions]

    def list_component_names(self) -> list[str]:
        """Get a complete list of all available TailwindPlus component names."""
        return list(self._components_by_name.keys())

    def get_component_by_name(
        self,
        name: Annotated[
            str,
            "The dotted path name of the component to retrieve (e.g., 'Application UI.Forms.Input Groups.Input with label')",
        ],
    ) -> Component:
        """Retrieve a specific TailwindPlus component by its dotted path name.

        If the component is not found, raises ComponentNotFoundError with up to 5
        suggested component names based on partial matches.
        """
        if name in self._components_by_name:
            return self._components_by_name[name]

        # Component not found, generate suggestions
        suggestions = self._suggestions_for_component_name(name, max_suggestions=5)
        raise ComponentNotFoundError(name, suggestions)

    def search_components_by_name(
        self,
        search_term: Annotated[
            str,
            "Search term to match against component names (case-insensitive, supports partial matches)",
        ],
    ) -> list[str]:
        """Search for TailwindPlus components by name pattern or keyword."""
        return self._suggestions_for_component_name(search_term)
