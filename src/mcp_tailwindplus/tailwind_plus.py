import hashlib
import json
import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

from packaging.version import Version
from platformdirs import user_cache_dir

from .component_text import extract_parts, extract_prose

# Bump when the cache's tables change, so caches built by older code are rebuilt.
CACHE_FORMAT = "2"

MAX_SEARCH_RESULTS = 50

# Far more words than any description of a component needs. Each word adds a
# prefix match to the full-text query, whose time grows faster than the number
# of words, so the cap keeps a long search term from running for minutes.
MAX_SEARCH_WORDS = 32

# Most components' prose is shorter; the cap keeps a few long pages, such as a
# full-year calendar, from dominating search results.
MAX_RESULT_PROSE_CHARS = 1500

# bm25 weights for the search index columns: full_name, parts,
# description, prose.
_SEARCH_COLUMN_WEIGHTS = (10.0, 5.0, 2.0, 1.0)

# Separates prose fragments and parts in the search index.
_TEXT_SEPARATOR = "\n"

# Marks the matched terms of a description in search queries.
_MATCH_START, _MATCH_END = "\x02", "\x03"


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


@dataclass
class SearchResult:
    """A component matching a search, with the text that describes it."""

    full_name: str
    prose: list[str]
    parts: list[str]
    # The component's subcategory description, only when it matched the search
    # and this is the subcategory's first result.
    description: str | None


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
        self._cache_path = self._get_cache_path(data_file, cache_dir)
        self._thread = threading.local()
        self._connections: list[sqlite3.Connection] = []
        self._connections_lock = threading.Lock()

        if self._cache_is_stale(self._cache_path, data_file):
            self._build_cache(data_file, self._cache_path)
        else:
            self._load_metadata_from_db()

        self._component_names = self._load_component_names()

    @property
    def _db(self) -> sqlite3.Connection:
        """The calling thread's connection to the cache.

        FastMCP runs tool calls in worker threads. The sqlite3 module reuses a
        connection's prepared statements, so calls sharing one connection can
        step the same statement at once and return each other's rows; each
        thread opens its own connection instead.
        """
        db = getattr(self._thread, "db", None)
        if db is None:
            db = self._connect_readonly(self._cache_path)
            with self._connections_lock:
                self._connections.append(db)
            self._thread.db = db
        return db

    def close(self) -> None:
        """Close the SQLite database connections of every thread."""
        # An instance whose construction failed early has no connections.
        if not hasattr(self, "_connections_lock"):
            return
        with self._connections_lock:
            for db in self._connections:
                db.close()

    def __enter__(self) -> "TailwindPlus":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    @staticmethod
    def _connect_readonly(cache_path: str) -> sqlite3.Connection:
        """Open the cache database read-only so any write raises instead of proceeding.

        Each thread has its own connection; opening read-only makes the
        read-only assumption explicit and enforced.
        """
        uri = f"{Path(cache_path).absolute().as_uri()}?mode=ro"
        db = sqlite3.connect(uri, uri=True, check_same_thread=False)
        db.row_factory = sqlite3.Row
        return db

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
            db = TailwindPlus._connect_readonly(cache_path)
            row = db.execute(
                "SELECT value FROM metadata WHERE key = 'cache_format'"
            ).fetchone()
            if row is None or row["value"] != CACHE_FORMAT:
                return True

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

        # The building thread's connection writes the new file; the build's
        # methods reach it as self._db.
        self._thread.db = sqlite3.connect(cache_path)
        try:
            self._db.row_factory = sqlite3.Row
            self._create_tables()
            # Data from downloaders before 4.0.0 has no descriptions.
            self._populate_db(
                raw_data["tailwindplus"], raw_data.get("descriptions", {})
            )
            self._store_metadata(data_file)
            self._db.commit()
            self._db.close()
        finally:
            # All further access is reads, through read-only connections.
            del self._thread.db

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
        # One row per component. The porter tokenizer stems words, so "dropdowns"
        # matches "dropdown".
        self._db.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS component_search USING fts5(
                full_name, parts, description, prose,
                tokenize = 'porter unicode61'
            )
            """
        )

    def _populate_db(self, tailwindplus_data: dict, descriptions: dict) -> None:
        """Traverse the JSON tree, insert snippets into the DB, and index each
        component for search."""

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
                    self._index_component(
                        component_name, value["snippets"], descriptions
                    )
                elif isinstance(value, dict):
                    traverse(value, current_path)

        traverse(tailwindplus_data)

    def _index_component(
        self, full_name: str, snippets: list[dict], descriptions: dict
    ) -> None:
        """Add a component's searchable text to the search index.

        Prose and parts come from one snippet per framework, since they are the
        same across frameworks and modes; Tailwind 4 snippets are preferred. The description is the subcategory's description and
        introduction. Product descriptions are left out: they list examples for
        the whole product, so they would match nearly every component.
        """

        def code(framework: str) -> str:
            by_version = {
                str(s["version"]): s["code"] for s in snippets if s["name"] == framework
            }
            return by_version.get("4", by_version.get("3", ""))

        html, react = code("html"), code("react")
        subcategory = ".".join(full_name.split(".")[:3])
        subcategory_text = descriptions.get("subcategories", {}).get(subcategory, {})
        description = " ".join(
            text
            for text in (
                subcategory_text.get("description"),
                subcategory_text.get("introduction"),
            )
            if text
        )

        self._db.execute(
            """
            INSERT INTO component_search (full_name, parts, description, prose)
            VALUES (?, ?, ?, ?)
            """,
            (
                full_name,
                _TEXT_SEPARATOR.join(extract_parts(html, react)),
                description,
                _TEXT_SEPARATOR.join(extract_prose(html)),
            ),
        )

    def _store_metadata(self, data_file: str) -> None:
        """Store metadata in the DB including source file stats for staleness checks."""
        stat = os.stat(data_file)
        metadata = {
            "cache_format": CACHE_FORMAT,
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
        row = self._db.execute(
            "SELECT * FROM snippets WHERE full_name=? AND framework=? "
            "AND tailwind_version=? AND mode=?",
            (full_name, framework.value, tailwind_version.value, mode.value),
        ).fetchone()
        return dict(row) if row else None

    def _suggestions_for_component_name(
        self, name: str, *, max_suggestions: int | None = None
    ) -> list[str]:
        """Generate component name suggestions based on partial matches."""
        name_parts = name.lower().split(".")

        suggestions = [
            comp_name
            for comp_name in self._component_names
            if any(part in comp_name.lower() for part in name_parts)
        ]

        return suggestions if max_suggestions is None else suggestions[:max_suggestions]

    @staticmethod
    def modes_for_product(product: str) -> list[Mode]:
        """Return the modes the components of a product support.

        Application UI and Marketing components support 'light', 'dark', and
        'system'; eCommerce components support only 'none'.
        """
        if product == "Ecommerce":
            return [Mode.NONE]
        return [Mode.LIGHT, Mode.DARK, Mode.SYSTEM]

    @classmethod
    def _validate_mode_for_component(cls, full_name: str, mode: Mode) -> None:
        """Validate that the mode matches the component's product."""
        product = full_name.split(".", 1)[0]
        if mode in cls.modes_for_product(product):
            return
        if mode != Mode.NONE:
            raise ValueError(
                f"eCommerce component '{full_name}' must use mode='none'. Got mode='{mode.value}'. eCommerce components only support mode='none'."
            )
        raise ValueError(
            f"Component '{full_name}' cannot use mode='none'. Got mode='{mode.value}'. Application UI and Marketing components support modes: 'light', 'dark', 'system'."
        )

    def _get_validated_snippet(
        self,
        full_name: str,
        framework: Framework,
        tailwind_version: TailwindVersion,
        mode: Mode,
    ) -> dict:
        """Validate the mode and fetch the snippet.

        Raises ComponentNotFoundError with up to 5 suggested component names if
        the component is not found.
        """
        self._validate_mode_for_component(full_name, mode)

        snippet = self._get_snippet(full_name, framework, tailwind_version, mode)

        if snippet is None:
            suggestions = self._suggestions_for_component_name(
                full_name, max_suggestions=5
            )
            raise ComponentNotFoundError(full_name, suggestions)

        return snippet

    def list_tailwindplus_information(self) -> dict[str, str | int]:
        """Get TailwindPlus metadata information including version, download date, component count, etc."""
        return {
            "version": self.version,
            "downloaded_at": self.downloaded_at,
            "component_count": self.component_count,
            "download_duration": self.download_duration,
            "downloader_version": self.downloader_version,
        }

    def list_component_names(
        self,
        prefix: Annotated[
            str,
            "Leading levels of the dotted name, such as 'Application UI.Forms', to list only that branch (case-insensitive); empty lists all components",
        ] = "",
    ) -> list[str]:
        """Get the TailwindPlus component names, sorted, optionally only those
        under a branch of the dotted name.

        The prefix matches whole levels, so 'Application UI.Forms' lists
        'Application UI.Forms.Input Groups.…' but would not list a sibling
        named 'Application UI.Formsets'.
        """
        branch = prefix.strip().rstrip(".").lower()
        return sorted(
            name
            for name in self._component_names
            if not branch
            or name.lower() == branch
            or name.lower().startswith(f"{branch}.")
        )

    def search_component_names(
        self,
        search_term: Annotated[
            str,
            "Words to search for, such as 'email input' or 'star rating' (case-insensitive; words may be partial). Icons are named by their shape, so search 'exclamation triangle' for a warning icon",
        ],
        limit: Annotated[
            int,
            f"Maximum number of results, 1 to {MAX_SEARCH_RESULTS}",
        ] = 10,
    ) -> list[SearchResult]:
        """Search components by name, visible text, named parts and subcategory
        description, best matches first.

        Components matching every word come first; when none do, components
        matching any word are returned. Repeated words are searched once, and
        only the first MAX_SEARCH_WORDS distinct words. Each result carries the
        component's
        visible prose (capped at MAX_RESULT_PROSE_CHARS) and parts. When a
        subcategory description matched, it comes with the subcategory's first
        result.
        """
        if not 1 <= limit <= MAX_SEARCH_RESULTS:
            raise ValueError(
                f"limit must be between 1 and {MAX_SEARCH_RESULTS}; got {limit}"
            )

        words = list(dict.fromkeys(re.findall(r"\w+", search_term.lower())))
        # Quote each word so FTS5 query syntax in the search term is matched as
        # text, and match it as a prefix so partial words match.
        terms = [f'"{word}"*' for word in words[:MAX_SEARCH_WORDS]]
        if not terms:
            return []

        for operator in (" AND ", " OR "):
            rows = self._db.execute(
                f"""
                SELECT
                    full_name,
                    parts,
                    prose,
                    highlight(component_search, 2, '{_MATCH_START}', '{_MATCH_END}')
                        AS description
                FROM component_search
                WHERE component_search MATCH ?
                ORDER BY bm25(component_search, {", ".join(map(str, _SEARCH_COLUMN_WEIGHTS))})
                LIMIT ?
                """,
                (operator.join(terms), limit),
            ).fetchall()
            if rows:
                break

        results = []
        described_subcategories = set()
        for row in rows:
            # Components of a subcategory share its description, so return it
            # only on the subcategory's first result.
            subcategory = row["full_name"].rsplit(".", 1)[0]
            description = None
            if (
                _MATCH_START in row["description"]
                and subcategory not in described_subcategories
            ):
                description = _strip_match_marks(row["description"])
                described_subcategories.add(subcategory)

            results.append(
                SearchResult(
                    full_name=row["full_name"],
                    prose=_capped_prose(_split_text(row["prose"])),
                    parts=_split_text(row["parts"]),
                    description=description,
                )
            )
        return results

    def component_name_levels(self, parent_levels: list[str]) -> list[str]:
        """Return the distinct name levels directly below the given parent levels.

        With no parent levels, return the products. For example, the parent levels
        ['Application UI', 'Forms'] return subcategories such as 'Input Groups'.
        """
        depth = len(parent_levels)
        return sorted(
            {
                levels[depth]
                for levels in (name.split(".") for name in self._component_names)
                if len(levels) > depth and levels[:depth] == parent_levels
            }
        )

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
        snippet = self._get_validated_snippet(
            full_name, framework, tailwind_version, mode
        )

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
        snippet = self._get_validated_snippet(
            full_name, framework, tailwind_version, mode
        )

        return snippet["preview"]


def _split_text(text: str) -> list[str]:
    """Split search index text back into its fragments."""
    return text.split(_TEXT_SEPARATOR) if text else []


def _capped_prose(fragments: list[str]) -> list[str]:
    """Keep the leading fragments within MAX_RESULT_PROSE_CHARS, marking a cut
    with a final '…'."""
    kept, length = [], 0
    for fragment in fragments:
        length += len(fragment)
        if length > MAX_RESULT_PROSE_CHARS:
            return [*kept, "…"]
        kept.append(fragment)
    return kept


def _strip_match_marks(text: str) -> str:
    """Remove the marks that search queries put around matched terms."""
    return text.replace(_MATCH_START, "").replace(_MATCH_END, "")
