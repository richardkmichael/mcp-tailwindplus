import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, TextIO


class Framework(Enum):
    HTML = "html"
    REACT = "react"
    VUE = "vue"


class Language(Enum):
    HTML = "html"
    JSX = "jsx"


class TailwindVersion(Enum):
    V3 = 3
    V4 = 4


class Mode(Enum):
    LIGHT = "light"
    DARK = "dark"


@dataclass
class Component:
    version: str
    name: str
    short_name: str
    code: str
    framework: Framework
    language: Language
    tailwind_version: TailwindVersion
    mode: Mode | None
    supportsDarkMode: bool



class ComponentNotFoundError(Exception):
    """Raised when a component is not found by its name."""

    def __init__(self, component_name: str, suggestions: list[str] | None = None):
        self.component_name = component_name
        self.suggestions = suggestions or []

        # Create a helpful error message
        message = f"Component `{component_name}` not found."

        if self.suggestions:
            quoted_suggestions = [f"`{suggestion}`" for suggestion in self.suggestions]
            message += f" Did you mean one of: {', '.join(quoted_suggestions)}?"

        super().__init__(message)


class TailwindPlus:
    def __init__(self, data_source: str | TextIO):
        if isinstance(data_source, str):
            # It's a file path
            with open(data_source) as f:
                raw_data = json.load(f)
        else:
            # It's a file-like object (StringIO, etc.)
            raw_data = json.load(data_source)

        # Extract version directly from JSON metadata
        self.version = raw_data["version"]
        
        # Build component index for O(1) lookups
        self._component_index = self._build_component_index(raw_data["tailwindplus"])

    def _build_component_index(self, tailwindplus_data: dict) -> dict[tuple[str, Framework, TailwindVersion], dict]:
        """Build lookup index for O(1) component access."""
        index = {}
        
        def traverse(obj: dict, path: list[str] = []):
            for key, value in obj.items():
                current_path = path + [key]
                
                if isinstance(value, dict) and "snippets" in value:
                    # Found a component - index all its snippets
                    component_name = ".".join(current_path)
                    for snippet in value["snippets"]:
                        framework = Framework(snippet["name"])  # html/react/vue
                        version = TailwindVersion(snippet["version"])  # 3/4
                        
                        lookup_key = (component_name, framework, version)
                        index[lookup_key] = snippet
                elif isinstance(value, dict):
                    # Keep traversing
                    traverse(value, current_path)
        
        traverse(tailwindplus_data)
        return index

    def _suggestions_for_component_name(
        self, name: str, *, max_suggestions: int | None = None
    ) -> list[str]:
        """Generate component name suggestions based on partial matches."""
        name_parts = [part.lower() for part in name.lower().split(".")]

        # Extract unique component names from index keys
        all_component_names = set(key[0] for key in self._component_index.keys())
        
        suggestions = [
            comp_name
            for comp_name in all_component_names
            if any(part in comp_name.lower() for part in name_parts)
        ]

        return suggestions if max_suggestions is None else suggestions[:max_suggestions]

    def list_component_names(self) -> list[str]:
        """Get a complete list of all available TailwindPlus component names."""
        # Extract unique component names from index keys
        unique_names = set(key[0] for key in self._component_index.keys())
        return sorted(list(unique_names))

    def get_component_by_name(
        self,
        name: Annotated[
            str,
            "The dotted path name of the component to retrieve (e.g., 'Application UI.Forms.Input Groups.Label with leading icon')",
        ],
        framework: Annotated[
            Framework,
            "REQUIRED: Must match user's project framework (html/react/vue)",
        ],
        tailwind_version: Annotated[
            TailwindVersion,
            "REQUIRED: Use 4 for new projects, 3 only if user specifically needs legacy version",
        ],
    ) -> Component:
        """Retrieve a specific TailwindPlus component by its dotted path name.

        If the component is not found, raises ComponentNotFoundError with up to 5
        suggested component names based on partial matches.
        """
        key = (name, framework, tailwind_version)
        
        if key not in self._component_index:
            # Component not found, generate suggestions
            suggestions = self._suggestions_for_component_name(name, max_suggestions=5)
            raise ComponentNotFoundError(name, suggestions)
        
        snippet_data = self._component_index[key]
        
        # Extract name parts
        # e.g., "Application UI.Forms.Input Groups.Label with leading icon" 
        # -> short_name = "Label with leading icon"
        name_parts = name.split(".")
        short_name = name_parts[-1]
        
        # Extract snippet properties
        code = snippet_data["code"]
        language_str = snippet_data["language"]
        mode_str = snippet_data["mode"]
        supports_dark_mode = snippet_data["supportsDarkMode"]
        
        # Convert to enums
        language = Language(language_str)
        mode = Mode(mode_str) if mode_str else None
        
        return Component(
            version=self.version,
            name=name,
            short_name=short_name,
            code=code,
            framework=framework,
            language=language,
            tailwind_version=tailwind_version,
            mode=mode,
            supportsDarkMode=supports_dark_mode
        )

    def get_component_preview_by_name(
        self,
        name: Annotated[
            str,
            "The dotted path name of the component to retrieve preview for (e.g., 'Application UI.Forms.Input Groups.Label with leading icon')",
        ],
        framework: Annotated[
            Framework,
            "REQUIRED: Must match user's project framework (html/react/vue)",
        ],
        tailwind_version: Annotated[
            TailwindVersion,
            "REQUIRED: Use 4 for new projects, 3 only if user specifically needs legacy version",
        ],
    ) -> str:
        """Retrieve the preview HTML for a specific TailwindPlus component.

        If the component is not found, raises ComponentNotFoundError with up to 5
        suggested component names based on partial matches.
        """
        key = (name, framework, tailwind_version)
        
        if key not in self._component_index:
            # Component not found, generate suggestions
            suggestions = self._suggestions_for_component_name(name, max_suggestions=5)
            raise ComponentNotFoundError(name, suggestions)
        
        snippet_data = self._component_index[key]
        return snippet_data["preview"]

    def search_component_names(
        self,
        search_term: Annotated[
            str,
            "Search term to match against component names (case-insensitive, supports partial matches)",
        ],
    ) -> list[str]:
        """Search for TailwindPlus component names by pattern or keyword."""
        return self._suggestions_for_component_name(search_term)
