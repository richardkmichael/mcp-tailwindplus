import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from packaging.version import Version
from platformdirs import user_cache_dir

# MCP Apps viewer template derived from the common TailwindPlus preview shell.
# The ontoolresult callback receives full preview HTML, extracts the <style>
# and <body> content, and injects them into this template's DOM.
_PREVIEW_VIEWER_HTML = """\
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<link rel="preconnect" href="https://rsms.me/">
<link rel="stylesheet" href="https://rsms.me/inter/inter.css">
<script src="https://cdn.jsdelivr.net/npm/@tailwindplus/elements@insiders" type="module"></script>
<style id="tw-component-css"></style>
<script src="/plus-assets/build/iframe/components.js?hash=25df7d34d043de1c316a31211aa744b1"></script>
<link rel="modulepreload" href="https://tailwindcss.com/plus-assets/build/assets/iframe-BUCe_xEG.js" />
<script type="module" src="https://tailwindcss.com/plus-assets/build/assets/iframe-BUCe_xEG.js"></script>
<style>body {{ -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }}</style>
<body>
<div id="preview-container"></div>
<script type="module">
  import {{ App }} from "https://unpkg.com/@modelcontextprotocol/ext-apps@1.2.2/app-with-deps";

  const app = new App({{ name: "TailwindPlus Preview", version: "{mcp_server_version}" }});

  app.ontoolresult = ({{ content }}) => {{
    const text = content?.find(c => c.type === "text");
    if (!text) return;

    const parser = new DOMParser();
    const doc = parser.parseFromString(text.text, "text/html");

    // Extract compiled component CSS from the preview HTML
    const styles = doc.querySelectorAll("style");
    let componentCSS = "";
    for (const style of styles) {{
      if (style.textContent.includes("tailwindcss")) {{
        componentCSS = style.textContent;
        break;
      }}
    }}
    document.getElementById("tw-component-css").textContent = componentCSS;

    // Extract component markup from the preview body
    document.getElementById("preview-container").innerHTML = doc.body.innerHTML;
  }};

  await app.connect();
</script>
</body>
"""


def get_preview_viewer_html() -> str:
    """Return the MCP Apps viewer HTML for rendering TailwindPlus component previews."""
    from importlib.metadata import version as mcp_server_version

    return _PREVIEW_VIEWER_HTML.format(
        mcp_server_version=mcp_server_version("mcp-tailwindplus")
    )


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
        framework = Framework(snippet_data["framework"])
        language = Language(snippet_data["language"])
        mode = Mode(snippet_data["mode"])
        tailwind_version = TailwindVersion(str(snippet_data["tailwind_version"]))

        return cls(
            version=version,
            full_name=full_name,
            name=name,
            code=snippet_data["code"],
            framework=framework,
            language=language,
            tailwind_version=tailwind_version,
            mode=mode,
            supportsDarkMode=bool(snippet_data["supports_dark_mode"]),
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
    def __init__(self, data_file: str, cache_dir: str | None = None):
        self._data_file = data_file
        cache_path = self._get_cache_path(data_file, cache_dir)

        if self._cache_is_stale(cache_path, data_file):
            self._build_cache(data_file, cache_path)
        else:
            self._db = sqlite3.connect(cache_path, check_same_thread=False)
            self._db.row_factory = sqlite3.Row
            self._load_metadata_from_db()

        self._component_names = self._load_component_names()

    def close(self) -> None:
        """Close the SQLite database connection."""
        if hasattr(self, "_db") and self._db:
            self._db.close()

    def __del__(self) -> None:
        self.close()

    @staticmethod
    def _get_cache_path(file_path: str, cache_dir: str | None = None) -> str:
        """Compute the SQLite cache path for a given data file."""
        abs_path = os.path.abspath(file_path)
        path_hash = hashlib.sha256(abs_path.encode()).hexdigest()[:16]
        if cache_dir is None:
            cache_dir = user_cache_dir("mcp-tailwindplus")
        return os.path.join(cache_dir, f"tailwindplus_components_cache_{path_hash}.db")

    @staticmethod
    def _cache_is_stale(cache_path: str, data_file: str) -> bool:
        """Check if the cache needs to be rebuilt."""
        if not os.path.exists(cache_path):
            return True

        db = None
        try:
            db = sqlite3.connect(cache_path)
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT value FROM metadata WHERE key = 'source_mtime'"
            ).fetchone()
            if row is None:
                return True
            stored_mtime = float(row["value"])

            row = db.execute(
                "SELECT value FROM metadata WHERE key = 'source_size'"
            ).fetchone()
            if row is None:
                return True
            stored_size = int(row["value"])

            stat = os.stat(data_file)
            return stat.st_mtime != stored_mtime or stat.st_size != stored_size
        except (sqlite3.DatabaseError, OSError):
            return True
        finally:
            if db is not None:
                db.close()

    def _build_cache(self, data_file: str, cache_path: str) -> None:
        """Parse JSON and build the SQLite cache."""
        with open(data_file) as f:
            raw_data = json.load(f)

        # Extract and validate metadata
        self.version = raw_data["version"]
        self.downloaded_at = raw_data["downloaded_at"]
        self.component_count = raw_data["component_count"]
        self.download_duration = raw_data["download_duration"]
        self.downloader_version = raw_data["downloader_version"]

        if Version(self.downloader_version) < Version("3.0.0-rc1"):
            raise ValueError(
                f"TailwindPlus data requires downloader version >= 3.0.0-rc1 for mode support. "
                f"Found version {self.downloader_version}. Please regenerate the data file with a newer downloader version."
            )

        # Create cache directory
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        # Create/overwrite the SQLite DB
        if os.path.exists(cache_path):
            os.remove(cache_path)

        self._db = sqlite3.connect(cache_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._create_tables()
        self._populate_db(raw_data["tailwindplus"])
        self._store_metadata(data_file)
        self._db.commit()

    def _create_tables(self) -> None:
        """Create the SQLite tables."""
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS snippets (
                full_name TEXT NOT NULL,
                framework TEXT NOT NULL,
                tailwind_version TEXT NOT NULL,
                mode TEXT NOT NULL,
                language TEXT NOT NULL,
                code TEXT NOT NULL,
                preview TEXT NOT NULL,
                supports_dark_mode INTEGER NOT NULL,
                PRIMARY KEY (full_name, framework, tailwind_version, mode)
            )
            """
        )

    def _populate_db(self, tailwindplus_data: dict) -> None:
        """Traverse the JSON tree and insert snippets into the DB."""

        def traverse(obj: dict, path: list[str] | None = None):
            if path is None:
                path = []
            for key, value in obj.items():
                current_path = path + [key]

                if isinstance(value, dict) and "snippets" in value:
                    component_name = ".".join(current_path)
                    for snippet in value["snippets"]:
                        framework = snippet["name"]  # html/react/vue
                        tailwind_version = str(snippet["version"])  # "3" or "4"
                        mode = snippet["mode"]
                        if mode is None:
                            mode = "none"

                        self._db.execute(
                            """
                            INSERT INTO snippets
                                (full_name, framework, tailwind_version, mode,
                                 language, code, preview, supports_dark_mode)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                component_name,
                                framework,
                                tailwind_version,
                                mode,
                                snippet["language"],
                                snippet["code"],
                                snippet["preview"],
                                1 if snippet["supportsDarkMode"] else 0,
                            ),
                        )
                elif isinstance(value, dict):
                    traverse(value, current_path)

        traverse(tailwindplus_data)

    def _store_metadata(self, data_file: str) -> None:
        """Store metadata in the DB including source file stats for staleness checks."""
        stat = os.stat(data_file)
        metadata = {
            "source_file": os.path.abspath(data_file),
            "source_mtime": str(stat.st_mtime),
            "source_size": str(stat.st_size),
            "version": self.version,
            "downloaded_at": self.downloaded_at,
            "component_count": str(self.component_count),
            "download_duration": self.download_duration,
            "downloader_version": self.downloader_version,
        }
        for key, value in metadata.items():
            self._db.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (key, value),
            )

    def _load_metadata_from_db(self) -> None:
        """Load metadata from the DB into instance attributes."""
        rows = self._db.execute("SELECT key, value FROM metadata").fetchall()
        meta = {row["key"]: row["value"] for row in rows}
        self.version = meta["version"]
        self.downloaded_at = meta["downloaded_at"]
        self.component_count = int(meta["component_count"])
        self.download_duration = meta["download_duration"]
        self.downloader_version = meta["downloader_version"]

    def _load_component_names(self) -> set[str]:
        """Load distinct component names from the DB."""
        rows = self._db.execute("SELECT DISTINCT full_name FROM snippets").fetchall()
        return {row["full_name"] for row in rows}

    def _get_snippet(
        self,
        full_name: str,
        framework: Framework,
        tailwind_version: TailwindVersion,
        mode: Mode,
    ) -> dict | None:
        """Retrieve a single snippet from the DB."""
        mode_val = "none" if mode == Mode.NONE else mode.value
        row = self._db.execute(
            "SELECT * FROM snippets WHERE full_name=? AND framework=? "
            "AND tailwind_version=? AND mode=?",
            (full_name, framework.value, tailwind_version.value, mode_val),
        ).fetchone()
        return dict(row) if row else None

    def _suggestions_for_component_name(
        self, name: str, *, max_suggestions: int | None = None
    ) -> list[str]:
        """Generate component name suggestions based on partial matches."""
        name_parts = [part.lower() for part in name.lower().split(".")]

        suggestions = [
            comp_name
            for comp_name in self._component_names
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
        return sorted(self._component_names)

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

        snippet = self._get_snippet(full_name, framework, tailwind_version, mode)

        if snippet is None:
            suggestions = self._suggestions_for_component_name(
                full_name, max_suggestions=5
            )
            raise ComponentNotFoundError(full_name, suggestions)

        return Component.from_snippet(snippet, self.version, full_name)

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

        snippet = self._get_snippet(full_name, framework, tailwind_version, mode)

        if snippet is None:
            suggestions = self._suggestions_for_component_name(
                full_name, max_suggestions=5
            )
            raise ComponentNotFoundError(full_name, suggestions)

        return snippet["preview"]

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
