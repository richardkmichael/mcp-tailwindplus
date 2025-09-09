import json
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, TextIO

from packaging.version import Version


class Framework(Enum):
    HTML = "html"
    REACT = "react"
    VUE = "vue"


class Language(Enum):
    HTML = "html"
    JSX = "jsx"


class TailwindVersion(Enum):
    V3 = "3"
    V4 = "4"


class Mode(Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    NONE = "none"

    @classmethod
    def _missing_(cls, value):
        # Handle Python None by mapping to Mode.NONE
        if value is None:
            return cls.NONE
        return None


@dataclass
class Component:
    version: str
    full_name: str
    name: str
    code: str
    framework: Framework
    language: Language
    tailwind_version: TailwindVersion
    mode: Mode
    supportsDarkMode: bool

    @classmethod
    def from_snippet(
        cls, snippet_data: dict, version: str, full_name: str
    ) -> "Component":
        """Create Component from raw snippet data."""
        name = full_name.split(".")[-1]
        framework = Framework(snippet_data["name"])
        language = Language(snippet_data["language"])
        mode = Mode(snippet_data["mode"])
        tailwind_version = TailwindVersion(str(snippet_data["version"]))

        return cls(
            version=version,
            full_name=full_name,
            name=name,
            code=snippet_data["code"],
            framework=framework,
            language=language,
            tailwind_version=tailwind_version,
            mode=mode,
            supportsDarkMode=snippet_data["supportsDarkMode"],
        )


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

        # Extract metadata directly from JSON
        self.version = raw_data["version"]
        self.downloaded_at = raw_data["downloaded_at"]
        self.component_count = raw_data["component_count"]
        self.download_duration = raw_data["download_duration"]
        self.downloader_version = raw_data["downloader_version"]

        # Validate downloader version requirement
        if Version(self.downloader_version) < Version("3.0.0-rc1"):
            raise ValueError(
                f"TailwindPlus data requires downloader version >= 3.0.0-rc1 for mode support. "
                f"Found version {self.downloader_version}. Please regenerate the data file with a newer downloader version."
            )

        # Build component index for O(1) lookups
        self._component_index = self._build_component_index(raw_data["tailwindplus"])

    def _build_component_index(
        self, tailwindplus_data: dict
    ) -> dict[tuple[str, Framework, TailwindVersion, Mode], dict]:
        """Build lookup index for O(1) component access."""
        index = {}

        def traverse(obj: dict, path: list[str] | None = None):
            if path is None:
                path = []
            for key, value in obj.items():
                current_path = path + [key]

                if isinstance(value, dict) and "snippets" in value:
                    # Found a component - index all its snippets
                    component_name = ".".join(current_path)
                    for snippet in value["snippets"]:
                        framework = Framework(snippet["name"])  # html/react/vue
                        version = TailwindVersion(
                            str(snippet["version"])
                        )  # "3"|"4", str for Enum
                        mode = Mode(snippet["mode"])

                        lookup_key = (component_name, framework, version, mode)
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
        all_component_names = {key[0] for key in self._component_index}

        suggestions = [
            comp_name
            for comp_name in all_component_names
            if any(part in comp_name.lower() for part in name_parts)
        ]

        return suggestions if max_suggestions is None else suggestions[:max_suggestions]

    def list_tailwindplus_information(self) -> dict[str, str | int]:
        """Get TailwindPlus metadata information including version, download date, component count, etc."""
        return {
            "version": self.version,
            "downloaded_at": self.downloaded_at,
            "component_count": self.component_count,
            "download_duration": self.download_duration,
            "downloader_version": self.downloader_version,
        }

    def list_component_names(self) -> list[str]:
        """Get a complete list of all available TailwindPlus component names."""
        # Extract unique component names from index keys
        unique_names = {key[0] for key in self._component_index}
        return sorted(unique_names)

    def search_component_names(
        self,
        search_term: Annotated[
            str,
            "Search term to match against component names (case-insensitive, supports partial matches)",
        ],
    ) -> list[str]:
        """Search for TailwindPlus component names by pattern or keyword."""
        return self._suggestions_for_component_name(search_term)

    def get_component_by_full_name(
        self,
        full_name: Annotated[
            str,
            "The full dotted path name of the component to retrieve (e.g., 'Application UI.Forms.Input Groups.Label with leading icon')",
        ],
        framework: Annotated[
            Framework,
            "REQUIRED: Target framework - 'html', 'react', or 'vue'",
        ],
        tailwind_version: Annotated[
            TailwindVersion,
            "REQUIRED: Tailwind CSS version - use '4' for new projects, '3' for legacy compatibility",
        ],
        mode: Annotated[
            Mode,
            "REQUIRED: Theme mode - use 'light', 'dark', or 'system' for Application UI/Marketing components; use 'none' for eCommerce components",
        ],
    ) -> Component:
        """Retrieve a specific TailwindPlus component by its full dotted path name.

        Validates that the mode parameter matches the component type:
        - Application UI and Marketing components require mode 'light', 'dark', or 'system'
        - eCommerce components require mode 'none'

        If the component is not found, raises ComponentNotFoundError with up to 5
        suggested component names based on partial matches.
        """
        # Validate mode matches component type
        if full_name.startswith("Ecommerce"):
            if mode != Mode.NONE:
                raise ValueError(
                    f"eCommerce component '{full_name}' must use mode='none'. Got mode='{mode.value}'. eCommerce components only support mode='none'."
                )
        else:
            if mode == Mode.NONE:
                raise ValueError(
                    f"Component '{full_name}' cannot use mode='none'. Got mode='{mode.value}'. Application UI and Marketing components support modes: 'light', 'dark', 'system'."
                )

        key = (full_name, framework, tailwind_version, mode)

        if key not in self._component_index:
            # Component not found, generate suggestions
            suggestions = self._suggestions_for_component_name(
                full_name, max_suggestions=5
            )
            raise ComponentNotFoundError(full_name, suggestions)

        snippet_data = self._component_index[key]

        return Component.from_snippet(snippet_data, self.version, full_name)

    def get_component_preview_by_full_name(
        self,
        full_name: Annotated[
            str,
            "The full dotted path name of the component to retrieve preview for (e.g., 'Application UI.Forms.Input Groups.Label with leading icon')",
        ],
        framework: Annotated[
            Framework,
            "REQUIRED: Target framework - 'html', 'react', or 'vue'",
        ],
        tailwind_version: Annotated[
            TailwindVersion,
            "REQUIRED: Tailwind CSS version - use '4' for new projects, '3' for legacy compatibility",
        ],
        mode: Annotated[
            Mode,
            "REQUIRED: Theme mode - use 'light', 'dark', or 'system' for Application UI/Marketing components; use 'none' for eCommerce components",
        ],
    ) -> str:
        """Retrieve the preview HTML for a specific TailwindPlus component.

        Validates that the mode parameter matches the component type:
        - Application UI and Marketing components require mode 'light', 'dark', or 'system'
        - eCommerce components require mode 'none'

        If the component is not found, raises ComponentNotFoundError with up to 5
        suggested component names based on partial matches.
        """
        # Validate mode matches component type
        if full_name.startswith("Ecommerce"):
            if mode != Mode.NONE:
                raise ValueError(
                    f"eCommerce component '{full_name}' must use mode='none'. Got mode='{mode.value}'. eCommerce components only support mode='none'."
                )
        else:
            # Application UI components must NOT use Mode.NONE
            if mode == Mode.NONE:
                raise ValueError(
                    f"Component '{full_name}' cannot use mode='none'. Got mode='{mode.value}'. Application UI and Marketing components support modes: 'light', 'dark', 'system'."
                )

        key = (full_name, framework, tailwind_version, mode)

        if key not in self._component_index:
            # Component not found, generate suggestions
            suggestions = self._suggestions_for_component_name(
                full_name, max_suggestions=5
            )
            raise ComponentNotFoundError(full_name, suggestions)

        snippet_data = self._component_index[key]
        return snippet_data["preview"]

    def get_component_as_resource(
        self,
        component_full_name: Annotated[
            str,
            "The full dotted path name of the component (e.g., 'Application UI.Forms.Input Groups.Label with leading icon')",
        ],
        framework: Annotated[
            str,
            "Target framework - 'html', 'react', or 'vue'",
        ],
        version: Annotated[
            str,
            "Tailwind CSS version - '3' or '4'",
        ],
        mode: Annotated[
            str,
            "REQUIRED: Theme mode - use 'light', 'dark', or 'system' for Application UI/Marketing components; use 'none' for eCommerce components",
        ],
    ) -> Component:
        """Get component code via resource path - adapter for get_component_by_full_name.

        Validates that the mode parameter matches the component type before retrieving the component.
        """
        framework_enum = Framework(framework)
        version_enum = TailwindVersion(version)
        # Convert string mode to enum, handling "none" -> None conversion
        mode_enum = Mode(mode)

        # Validate mode matches component type (same as main method)
        if component_full_name.startswith("Ecommerce"):
            if mode_enum != Mode.NONE:
                raise ValueError(
                    f"eCommerce component '{component_full_name}' must use mode='none'. Got mode='{mode}'. eCommerce components only support mode='none'."
                )
        else:
            if mode_enum == Mode.NONE:
                raise ValueError(
                    f"Component '{component_full_name}' cannot use mode='none'. Got mode='{mode}'. Application UI and Marketing components support modes: 'light', 'dark', 'system'."
                )

        return self.get_component_by_full_name(
            component_full_name, framework_enum, version_enum, mode_enum
        )

    def get_component_preview_as_resource(
        self,
        component_full_name: Annotated[
            str,
            "The full dotted path name of the component (e.g., 'Application UI.Forms.Input Groups.Label with leading icon')",
        ],
        framework: Annotated[
            str,
            "Target framework - 'html', 'react', or 'vue'",
        ],
        version: Annotated[
            str,
            "Tailwind CSS version - '3' or '4'",
        ],
        mode: Annotated[
            str,
            "REQUIRED: Theme mode - use 'light', 'dark', or 'system' for Application UI/Marketing components; use 'none' for eCommerce components",
        ],
    ) -> str:
        """Get component preview HTML via resource path - adapter for get_component_preview_by_full_name.

        Validates that the mode parameter matches the component type before retrieving the preview.
        """
        framework_enum = Framework(framework)
        version_enum = TailwindVersion(version)
        mode_enum = Mode(mode)

        # Validate mode matches component type (same as main method)
        if component_full_name.startswith("Ecommerce"):
            if mode_enum != Mode.NONE:
                raise ValueError(
                    f"eCommerce component '{component_full_name}' must use mode='none'. Got mode='{mode}'. eCommerce components only support mode='none'."
                )
        else:
            if mode_enum == Mode.NONE:
                raise ValueError(
                    f"Component '{component_full_name}' cannot use mode='none'. Got mode='{mode}'. Application UI and Marketing components support modes: 'light', 'dark', 'system'."
                )

        return self.get_component_preview_by_full_name(
            component_full_name, framework_enum, version_enum, mode_enum
        )
