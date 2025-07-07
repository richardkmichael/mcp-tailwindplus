import json
import os
from typing import Annotated, TextIO

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

        if isinstance(data_source, str):
            # It's a file path
            with open(data_source) as f:
                self.data = json.load(f)
        else:
            # It's a file-like object (StringIO, etc.)
            self.data = json.load(data_source)

        # Cache component names for list/search operations
        self._component_names = self._get_component_paths(self.data)

    def _get_component_paths(self, obj, prefix=""):
        """Recursively get all component paths as a list."""
        paths = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = ".".join([prefix, key]) if prefix else key

                # If value is not a dict, it's a leaf
                if not isinstance(value, dict):
                    paths.append(current_path)
                # If dict has no dict children (all values are strings), then each key is a component
                elif not any(isinstance(v, dict) for v in value.values()):
                    # All values are strings (HTML), so each key at this level is a component
                    for component_key in value.keys():
                        component_path = ".".join([current_path, component_key])
                        paths.append(component_path)
                else:
                    # Recurse deeper
                    paths.extend(self._get_component_paths(value, current_path))

        return paths

    def _suggestions_for_component_name(
        self, name: str, max_suggestions: int = 5
    ) -> list[str]:
        """Generate component name suggestions based on partial matches."""
        name_parts = [part.lower() for part in name.lower().split(".")]

        suggestions = [
            comp_name
            for comp_name in self._component_names
            if any(part in comp_name.lower() for part in name_parts)
        ]

        return suggestions[:max_suggestions]

    def _get_by_path(self, path: str) -> dict:
        """Efficiently get component data by dotted path without full flattening."""
        keys = path.split(".")
        current = self.data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return {}

        return current

    def list_component_names(self) -> list[str]:
        """Get a complete list of all available TailwindPlus component names."""
        return self._component_names

    def get_component_by_name(
        self, name: Annotated[str, "The dotted path name of the component to retrieve"]
    ) -> dict:
        """Retrieve a specific TailwindPlus component by its dotted path name."""
        component_data = self._get_by_path(name)

        # If component doesn't exist, raise our custom exception
        if not component_data:
            suggestions = self._suggestions_for_component_name(name)
            raise ComponentNotFoundError(name, suggestions)

        return {name: component_data}

    def search_components_by_name(
        self,
        search_term: Annotated[str, "The search term to match against component names"],
    ) -> list[str]:
        """Search for TailwindPlus components by name pattern or keyword."""
        return [
            name
            for name in self._component_names
            if search_term.lower() in name.lower()
        ]
