import glob
import hashlib
import json
import math
import multiprocessing
import os
import re
import sqlite3
import tempfile
import threading
import time
from array import array
from collections import defaultdict
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

import orjson

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
from packaging.version import Version
from platformdirs import user_cache_dir

from .component_structure import extract_structure
from .component_text import extract_parts, extract_prose

# Bump when the cache's tables change, so caches built by older code are rebuilt.
CACHE_FORMAT = "3"

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

# Below this many snippets, parsing their code takes less time than starting
# worker processes to parse it.
_PARALLEL_PARSING_MIN_SNIPPETS = 1000

# Snippet ids in the structure index are packed as unsigned 32-bit integers, in
# the machine's byte order; caches are built and read on the same machine.
_SNIPPET_ID_TYPECODE = "I"

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


@dataclass
class CodeMatch:
    """A component variant that code may have been copied from."""

    full_name: str
    tailwind_version: TailwindVersion
    mode: Mode
    # From 0 to 1; 1 is code with exactly the component's classes and elements.
    similarity: float


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
            with _build_lock(self._cache_path):
                # Another server may have built the cache while this one waited.
                if self._cache_is_stale(self._cache_path, data_file):
                    self._build_cache(data_file, self._cache_path)
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
        # The data file is hundreds of megabytes; orjson parses it about three
        # times faster than the json module.
        raw_data = orjson.loads(Path(data_file).read_bytes())

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

        # Build into a new file that replaces the cache only once complete, so
        # an interrupted build never leaves a partial cache in its place. That
        # also makes the journal and syncing to disk unnecessary while building.
        # A killed build leaves its file behind; the build lock is held, so no
        # other build is writing such files and they can be removed.
        for stale_build_path in glob.glob(f"{glob.escape(cache_path)}.*.building"):
            try:
                os.remove(stale_build_path)
            except OSError:
                pass
        build_fd, build_path = tempfile.mkstemp(
            dir=os.path.dirname(cache_path),
            prefix=f"{os.path.basename(cache_path)}.",
            suffix=".building",
        )
        os.close(build_fd)
        # The building thread's connection writes the new file; the build's
        # methods reach it as self._db.
        self._thread.db = sqlite3.connect(build_path)
        try:
            self._db.row_factory = sqlite3.Row
            # Large pages cut the writes of the build's large rows of code and
            # previews by more than half, for a cache about 8% larger.
            self._db.execute("PRAGMA page_size = 65536")
            self._db.execute("PRAGMA journal_mode = OFF")
            self._db.execute("PRAGMA synchronous = OFF")
            self._create_tables()
            # Data from downloaders before 4.0.0 has no descriptions.
            self._populate_db(
                raw_data["tailwindplus"], raw_data.get("descriptions", {})
            )
            self._store_metadata(data_file)
            self._db.commit()
            self._db.close()
            os.replace(build_path, cache_path)
        except BaseException:
            self._db.close()
            os.remove(build_path)
            raise
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
        # A component's frameworks share its previews, so each distinct preview
        # is stored once.
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS previews (
                id INTEGER PRIMARY KEY,
                html TEXT NOT NULL
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
                preview_id INTEGER NOT NULL REFERENCES previews (id),
                supports_dark_mode INTEGER NOT NULL,
                PRIMARY KEY (full_name, framework, tailwind_version, mode)
            )
            """
        )
        # The structure index: each snippet with the summed weight of its
        # structure tokens, and each token with its weight per framework and the
        # snippets having it. Snippet rows hold code and previews, so the index
        # has its own narrow snippet table to keep matching fast.
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS structure_snippets (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                framework TEXT NOT NULL,
                tailwind_version TEXT NOT NULL,
                mode TEXT NOT NULL,
                weight REAL NOT NULL
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS structure_tokens (
                id INTEGER PRIMARY KEY,
                framework TEXT NOT NULL,
                token TEXT NOT NULL,
                weight REAL NOT NULL,
                -- The ids of the snippets having the token, packed as
                -- _SNIPPET_ID_TYPECODE array items: one row per token, instead
                -- of one per token of each snippet, keeps the build's writes few.
                snippet_ids BLOB NOT NULL,
                UNIQUE (framework, token)
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
        """Insert snippets into the DB, and index each component for search and
        each snippet by its structure.

        Code is parsed for searchable text and structure, in worker processes
        when there is much of it, while the snippets are written.
        """
        components = list(_components(tailwindplus_data))
        snippets = [
            (full_name, snippet)
            for full_name, component_snippets in components
            for snippet in component_snippets
        ]
        with _worker_pool(len(snippets)) as pool:
            texts = _Mapped(
                _component_text,
                [
                    _text_code(component_snippets)
                    for _, component_snippets in components
                ],
                pool,
            )
            structures = _Mapped(
                extract_structure,
                [
                    (snippet["code"], snippet["language"] == Language.JSX.value)
                    for _, snippet in snippets
                ],
                pool,
            )

            preview_ids: dict[str, int] = {}
            for full_name, snippet in snippets:
                preview_id = preview_ids.get(snippet["preview"])
                if preview_id is None:
                    preview_id = self._db.execute(
                        "INSERT INTO previews (html) VALUES (?)",
                        (snippet["preview"],),
                    ).lastrowid
                    preview_ids[snippet["preview"]] = preview_id

                self._db.execute(
                    """
                    INSERT INTO snippets
                        (full_name, framework, tailwind_version, mode,
                         language, code, preview_id, supports_dark_mode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        full_name,
                        *_variant(snippet),
                        snippet["language"],
                        snippet["code"],
                        preview_id,
                        1 if snippet["supportsDarkMode"] else 0,
                    ),
                )

            for (full_name, _), (parts, prose) in zip(
                components, texts.results(), strict=True
            ):
                self._index_component(full_name, parts, prose, descriptions)

            tokens = structures.results()

        tokens_by_framework: dict[
            str, list[tuple[tuple[str, str, str], frozenset[str]]]
        ] = {}
        for (full_name, snippet), snippet_tokens in zip(snippets, tokens, strict=True):
            framework, tailwind_version, mode = _variant(snippet)
            tokens_by_framework.setdefault(framework, []).append(
                ((full_name, tailwind_version, mode), snippet_tokens)
            )
        self._index_structure(tokens_by_framework)

    def _index_component(
        self, full_name: str, parts: list[str], prose: list[str], descriptions: dict
    ) -> None:
        """Add a component's parts, prose and description to the search index.

        The description is the subcategory's description and introduction.
        Product descriptions are left out: they list examples for the whole
        product, so they would match nearly every component.
        """
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
                _TEXT_SEPARATOR.join(parts),
                description,
                _TEXT_SEPARATOR.join(prose),
            ),
        )

    def _index_structure(
        self,
        structures: dict[str, list[tuple[tuple[str, str, str], frozenset[str]]]],
    ) -> None:
        """Store each snippet's structure tokens, weighted by rarity.

        Given N snippets of a framework, n of which have a token, the token
        weighs log(1 + N / n), so tokens nearly every snippet has, such as
        `class:flex`, count for little, and a token every snippet has still
        counts.
        """
        token_rows, snippet_rows = [], []
        for framework, snippets in structures.items():
            snippet_ids_by_token: dict[str, array] = {}
            for (full_name, tailwind_version, mode), tokens in snippets:
                snippet_id = len(snippet_rows) + 1
                snippet_rows.append(
                    [snippet_id, full_name, framework, tailwind_version, mode]
                )
                for token in tokens:
                    snippet_ids = snippet_ids_by_token.get(token)
                    if snippet_ids is None:
                        snippet_ids = snippet_ids_by_token[token] = array(
                            _SNIPPET_ID_TYPECODE
                        )
                    snippet_ids.append(snippet_id)

            weights = {
                token: math.log(1 + len(snippets) / len(snippet_ids))
                for token, snippet_ids in snippet_ids_by_token.items()
            }
            token_rows.extend(
                (framework, token, weights[token], snippet_ids.tobytes())
                for token, snippet_ids in snippet_ids_by_token.items()
            )
            first_row = len(snippet_rows) - len(snippets)
            for row, (_, tokens) in zip(
                snippet_rows[first_row:], snippets, strict=True
            ):
                row.append(sum(weights[token] for token in tokens))

        self._db.executemany(
            "INSERT INTO structure_tokens (framework, token, weight, snippet_ids) "
            "VALUES (?, ?, ?, ?)",
            token_rows,
        )
        self._db.executemany(
            """
            INSERT INTO structure_snippets
                (id, full_name, framework, tailwind_version, mode, weight)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            snippet_rows,
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
            """
            SELECT snippets.*, previews.html AS preview
            FROM snippets JOIN previews ON previews.id = snippets.preview_id
            WHERE full_name=? AND framework=? AND tailwind_version=? AND mode=?
            """,
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

    def search_components_by_code(
        self,
        code: Annotated[
            str,
            "HTML, JSX or Vue template code, such as a TailwindPlus component copied into a project and edited since, or part of one",
        ],
        framework: Annotated[
            Framework,
            "The code's framework - 'html', 'react', or 'vue'",
        ],
        limit: Annotated[
            int,
            f"Maximum number of results, 1 to {MAX_SEARCH_RESULTS}",
        ] = 5,
    ) -> list[CodeMatch]:
        """Find the components code was most likely copied from, best matches
        first, each with its closest Tailwind version and mode.

        Code and component variants are compared by their structure tokens (see
        extract_structure), weighted by rarity. A variant's similarity is the
        mean of two shares of token weight: the share of the code's tokens the
        variant has, which stays high for code copied from part of a component,
        and the share of their tokens combined that both have, which favors
        variants of the code's size.
        """
        if not 1 <= limit <= MAX_SEARCH_RESULTS:
            raise ValueError(
                f"limit must be between 1 and {MAX_SEARCH_RESULTS}; got {limit}"
            )

        tokens = extract_structure(code, jsx=framework is Framework.REACT)
        if not tokens:
            return []
        token_list = json.dumps(sorted(tokens))

        shared_weights: dict[int, float] = defaultdict(float)
        known_weight, known_count = 0.0, 0
        for row in self._db.execute(
            """
            SELECT weight, snippet_ids FROM structure_tokens
            WHERE framework = ? AND token IN (SELECT value FROM json_each(?))
            """,
            (framework.value, token_list),
        ):
            weight = row["weight"]
            known_weight += weight
            known_count += 1
            snippet_ids = array(_SNIPPET_ID_TYPECODE)
            snippet_ids.frombytes(row["snippet_ids"])
            for snippet_id in snippet_ids:
                shared_weights[snippet_id] += weight

        (snippet_count,) = self._db.execute(
            "SELECT COUNT(*) FROM structure_snippets WHERE framework = ?",
            (framework.value,),
        ).fetchone()
        # A token no snippet has weighs as much as one only a single snippet has.
        unknown_weight = math.log(1 + snippet_count)
        code_weight = known_weight + (len(tokens) - known_count) * unknown_weight

        rows = self._db.execute(
            """
            SELECT id, full_name, tailwind_version, mode, weight
            FROM structure_snippets
            WHERE id IN (SELECT value FROM json_each(?))
            """,
            (json.dumps(list(shared_weights)),),
        )

        best: dict[str, CodeMatch] = {}
        for row in rows:
            shared_weight = shared_weights[row["id"]]
            containment = shared_weight / code_weight
            jaccard = shared_weight / (code_weight + row["weight"] - shared_weight)
            similarity = (containment + jaccard) / 2
            full_name = row["full_name"]
            if full_name not in best or similarity > best[full_name].similarity:
                best[full_name] = CodeMatch(
                    full_name=full_name,
                    tailwind_version=TailwindVersion(row["tailwind_version"]),
                    mode=Mode(row["mode"]),
                    similarity=similarity,
                )

        ranked = sorted(
            best.values(), key=lambda match: (-match.similarity, match.full_name)
        )
        for match in ranked[:limit]:
            match.similarity = round(match.similarity, 3)
        return ranked[:limit]

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


@contextmanager
def _build_lock(cache_path: str) -> Iterator[None]:
    """Hold an exclusive lock on the cache's lock file, creating the cache
    directory if needed, so servers starting at once build the cache one at a
    time.

    Without fcntl, on Windows, no lock is taken, and servers starting at once
    each build the cache; the last build to finish replaces the others.
    """
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if fcntl is None:
        yield
        return
    with open(f"{cache_path}.lock", "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield


def _components(tailwindplus_data: dict) -> Iterator[tuple[str, list[dict]]]:
    """Yield each component's full name and snippets from the data's tree."""

    def walk(node: dict, path: list[str]) -> Iterator[tuple[str, list[dict]]]:
        for key, value in node.items():
            if isinstance(value, dict) and "snippets" in value:
                yield ".".join([*path, key]), value["snippets"]
            elif isinstance(value, dict):
                yield from walk(value, [*path, key])

    return walk(tailwindplus_data, [])


def _variant(snippet: dict) -> tuple[str, str, str]:
    """Return a snippet's framework, Tailwind version and mode as stored."""
    return snippet["name"], str(snippet["version"]), snippet["mode"] or "none"


def _text_code(snippets: list[dict]) -> tuple[str, str]:
    """Return the HTML and React code a component's searchable text comes from.

    Prose and parts are the same across frameworks and modes, so they come from
    one snippet per framework; Tailwind 4 snippets are preferred.
    """

    def code(framework: str) -> str:
        by_version = {
            str(s["version"]): s["code"] for s in snippets if s["name"] == framework
        }
        return by_version.get("4", by_version.get("3", ""))

    return code("html"), code("react")


def _component_text(html: str, react: str) -> tuple[list[str], list[str]]:
    """Return a component's parts and prose."""
    return extract_parts(html, react), extract_prose(html)


@contextmanager
def _worker_pool(snippet_count: int) -> Iterator[ProcessPoolExecutor | None]:
    """Yield worker processes for parsing code, or None when there are too few
    snippets to repay starting them.

    One CPU is left for the caller's work. Workers are spawned, not forked,
    because forking a process that may run threads can deadlock the child.
    """
    if snippet_count < _PARALLEL_PARSING_MIN_SNIPPETS:
        yield None
        return
    pool = ProcessPoolExecutor(
        max_workers=max(1, (os.process_cpu_count() or 2) - 1),
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_exit_with_parent,
        initargs=(os.getpid(),),
    )
    try:
        yield pool
    finally:
        pool.shutdown(cancel_futures=True)


def _exit_with_parent(parent_pid: int) -> None:
    """Start a thread that ends this worker process once its parent is gone.

    A server killed outright, as by SIGKILL, cannot shut its workers down,
    and they would otherwise wait for work indefinitely. An orphaned process
    is given a new parent, so its parent process id changes; on Windows it
    does not, and workers outlive a killed server as before.
    """

    def watch() -> None:
        while os.getppid() == parent_pid:
            time.sleep(1)
        os._exit(1)

    threading.Thread(target=watch, daemon=True).start()


class _Mapped[Result]:
    """A function's results for each of a list of argument tuples, computed
    once per distinct tuple.

    With a worker pool, they are computed in the workers while the caller does
    other work; without one, when they are asked for.
    """

    def __init__(
        self,
        function: Callable[..., Result],
        arguments: list[tuple],
        pool: ProcessPoolExecutor | None,
    ) -> None:
        self._function = function
        self._arguments = arguments
        self._unique_arguments = list(dict.fromkeys(arguments))
        self._pending = None
        if pool is not None and self._unique_arguments:
            # Submits every task now; the results are collected in order.
            self._pending = pool.map(
                function, *zip(*self._unique_arguments, strict=True), chunksize=64
            )

    def results(self) -> list[Result]:
        """Return the result for each argument tuple, in order."""
        if self._pending is None:
            unique_results = [
                self._function(*arguments) for arguments in self._unique_arguments
            ]
        else:
            unique_results = list(self._pending)
        results_by_arguments = dict(
            zip(self._unique_arguments, unique_results, strict=True)
        )
        return [results_by_arguments[arguments] for arguments in self._arguments]


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
