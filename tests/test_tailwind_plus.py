import json
import os
import sqlite3
import threading
import time
from array import array
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import pytest

from mcp_tailwindplus import tailwind_plus
from mcp_tailwindplus.tailwind_plus import (
    MAX_RESULT_PROSE_CHARS,
    MAX_SEARCH_RESULTS,
    MAX_SEARCH_WORDS,
    CodeMatch,
    Component,
    ComponentNotFoundError,
    Framework,
    Language,
    Mode,
    TailwindPlus,
    TailwindVersion,
    _capped_prose,
)


@pytest.fixture
def sample_data():
    """Fragment of real TailwindPlus component data for testing with new format."""
    return {
        "version": "test-2025-07-15",
        "downloaded_at": "2025-07-15T00:00:00.000Z",
        "component_count": 4,
        "download_duration": "1.0s",
        "downloader_version": "3.0.0",
        "descriptions": {
            "products": {
                "Application UI": {"description": "Form layouts, tables, modal dialogs"}
            },
            "subcategories": {
                "Application UI.Navigation.Breadcrumbs": {
                    "description": "Breadcrumb examples for Tailwind CSS.",
                    "introduction": "Show users where they are in a site hierarchy.",
                }
            },
        },
        "tailwindplus": {
            "Application UI": {
                "Forms": {
                    "Input Groups": {
                        "Label with leading icon": {
                            "name": "Label with leading icon",
                            "snippets": [
                                {
                                    "code": """<div>
  <label for="email" class="block text-sm font-medium leading-6 text-gray-900">Email</label>
  <div class="relative mt-2 rounded-md shadow-sm">
    <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
      <svg class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path d="M3 4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2-2V4z" />
      </svg>
    </div>
    <input type="email" name="email" id="email" class="block w-full rounded-md border-0 py-1.5 pl-10 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6" placeholder="you@example.com">
  </div>
</div>""",
                                    "language": "html",
                                    "mode": "light",
                                    "name": "html",
                                    "preview": "<div>Email input preview</div>",
                                    "supportsDarkMode": False,
                                    "version": 4,
                                },
                                {
                                    "code": """import { EnvelopeIcon } from '@heroicons/react/20/solid'

<div>
  <label for="email" class="block text-sm font-medium leading-6 text-gray-900">Email</label>
  <div class="relative mt-2 rounded-md shadow-sm">
    <input type="email" name="email" id="email" class="block w-full rounded-md border-0 py-1.5 pl-10 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6" placeholder="you@example.com">
  </div>
</div>""",
                                    "language": "jsx",
                                    "mode": "light",
                                    "name": "react",
                                    "preview": "<div>Email input React preview</div>",
                                    "supportsDarkMode": False,
                                    "version": 4,
                                },
                            ],
                        }
                    },
                    "Select Menus": {
                        "Simple": {
                            "name": "Simple",
                            "snippets": [
                                {
                                    "code": """<div>
  <label for="location" class="block text-sm font-medium leading-6 text-gray-900">Location</label>
  <select id="location" name="location" class="mt-2 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6">
    <option>United States</option>
    <option>Canada</option>
    <option>Mexico</option>
  </select>
</div>""",
                                    "language": "html",
                                    "mode": "light",
                                    "name": "html",
                                    "preview": "<div>Select menu preview</div>",
                                    "supportsDarkMode": True,
                                    "version": 4,
                                }
                            ],
                        }
                    },
                },
                "Navigation": {
                    "Breadcrumbs": {
                        "Simple": {
                            "name": "Simple",
                            "snippets": [
                                {
                                    "code": """<nav class="flex" aria-label="Breadcrumb">
  <ol role="list" class="flex items-center space-x-4">
    <li>
      <div>
        <a href="#" class="text-gray-400 hover:text-gray-500">
          <svg class="h-5 w-5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 10v8a1 1 0 01-1 1h-2a1 1 0 01-1-1v-3a1 1 0 00-1-1H8a1 1 0 00-1 1v3a1 1 0 01-1 1H4a1 1 0 01-1-1v-8a1 1 0 01.293-.707l7-7z" clip-rule="evenodd" />
          </svg>
          <span class="sr-only">Home</span>
        </a>
      </div>
    </li>
    <li>
      <div class="flex items-center">
        <svg class="h-5 w-5 flex-shrink-0 text-gray-300" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
          <path d="M5.555 17.776l8-16 .894.448-8 16-.894-.448z" />
        </svg>
        <a href="#" class="ml-4 text-sm font-medium text-gray-500 hover:text-gray-700">Projects</a>
      </div>
    </li>
  </ol>
</nav>""",
                                    "language": "html",
                                    "mode": None,
                                    "name": "html",
                                    "preview": "<nav>Breadcrumb preview</nav>",
                                    "supportsDarkMode": False,
                                    "version": 4,
                                }
                            ],
                        }
                    }
                },
            },
            "Ecommerce": {
                "Product Lists": {
                    "Simple": {
                        "name": "Simple",
                        "snippets": [
                            {
                                "code": """<div class="bg-white">
  <div class="mx-auto max-w-2xl px-4 py-16 sm:px-6 sm:py-24 lg:max-w-7xl lg:px-8">
    <h2 class="text-2xl font-bold tracking-tight text-gray-900">Customers also purchased</h2>
    <div class="mt-6 grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-4 xl:gap-x-8">
      <div class="group relative">
        <div class="aspect-h-1 aspect-w-1 w-full overflow-hidden rounded-md bg-gray-200 lg:aspect-none group-hover:opacity-75 lg:h-80">
          <img src="#" alt="Product" class="h-full w-full object-cover object-center lg:h-full lg:w-full">
        </div>
        <div class="mt-4 flex justify-between">
          <div>
            <h3 class="text-sm text-gray-700">Basic Tee</h3>
            <p class="mt-1 text-sm text-gray-500">Black</p>
          </div>
          <p class="text-sm font-medium text-gray-900">$35</p>
        </div>
      </div>
    </div>
  </div>
</div>""",
                                "language": "html",
                                "mode": None,
                                "name": "html",
                                "preview": "<div>Product list preview</div>",
                                "supportsDarkMode": False,
                                "version": 4,
                            }
                        ],
                    }
                }
            },
        },
    }


@pytest.fixture
def data_file(sample_data, tmp_path):
    """Write sample data to a temp file and return its path."""
    path = tmp_path / "test-data.json"
    path.write_text(json.dumps(sample_data))
    return str(path)


@pytest.fixture
def tailwind_plus_instance(data_file, tmp_path):
    """Create a TailwindPlus instance from the temp data file."""
    with TailwindPlus(data_file, cache_dir=str(tmp_path)) as instance:
        yield instance


class TestTailwindPlus:
    def test_init_loads_data(self, tailwind_plus_instance, sample_data):
        """Test that initialization loads data correctly."""
        assert tailwind_plus_instance.version == "test-2025-07-15"
        assert len(tailwind_plus_instance.list_component_names()) > 0

    def test_get_component_paths(self, tailwind_plus_instance):
        """Test that component paths are extracted correctly."""
        expected_paths = [
            "Application UI.Forms.Input Groups.Label with leading icon",
            "Application UI.Forms.Select Menus.Simple",
            "Application UI.Navigation.Breadcrumbs.Simple",
            "Ecommerce.Product Lists.Simple",
        ]

        paths = tailwind_plus_instance.list_component_names()
        assert sorted(paths) == sorted(expected_paths)

    def test_list_component_names(self, tailwind_plus_instance):
        """Test listing all component names."""
        names = tailwind_plus_instance.list_component_names()

        assert isinstance(names, list)
        assert len(names) == 4
        assert "Application UI.Forms.Input Groups.Label with leading icon" in names
        assert "Application UI.Forms.Select Menus.Simple" in names
        assert "Application UI.Navigation.Breadcrumbs.Simple" in names
        assert "Ecommerce.Product Lists.Simple" in names

    @pytest.mark.parametrize(
        ("prefix", "expected"),
        [
            (
                "Application UI.Forms",
                [
                    "Application UI.Forms.Input Groups.Label with leading icon",
                    "Application UI.Forms.Select Menus.Simple",
                ],
            ),
            (
                "application ui.forms.",
                [
                    "Application UI.Forms.Input Groups.Label with leading icon",
                    "Application UI.Forms.Select Menus.Simple",
                ],
            ),
            ("Ecommerce", ["Ecommerce.Product Lists.Simple"]),
            ("Ecommerce.Product Lists.Simple", ["Ecommerce.Product Lists.Simple"]),
            ("Application UI.Form", []),
            ("Marketing", []),
        ],
    )
    def test_list_component_names_by_prefix(
        self, tailwind_plus_instance, prefix, expected
    ):
        """The prefix matches whole levels of the dotted name, ignoring case."""
        assert tailwind_plus_instance.list_component_names(prefix) == expected

    def test_get_component_by_full_name_exists(self, tailwind_plus_instance):
        """Test getting an existing component by full name."""
        result = tailwind_plus_instance.get_component_by_full_name(
            "Application UI.Forms.Input Groups.Label with leading icon",
            Framework.HTML,
            TailwindVersion.V4,
            Mode.LIGHT,
        )

        assert isinstance(result, Component)
        assert (
            result.full_name
            == "Application UI.Forms.Input Groups.Label with leading icon"
        )
        assert result.name == "Label with leading icon"
        assert result.version == "test-2025-07-15"
        assert result.framework == Framework.HTML
        assert result.language == Language.HTML
        assert result.tailwind_version == TailwindVersion.V4
        assert result.mode == Mode.LIGHT
        assert not result.supportsDarkMode
        assert isinstance(result.code, str)
        assert "Email" in result.code

    def test_get_component_by_full_name_not_exists(self, tailwind_plus_instance):
        """Test getting a non-existent component by name."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "nonexistent.component", Framework.HTML, TailwindVersion.V4, Mode.LIGHT
            )

        assert exc_info.value.component_name == "nonexistent.component"

    def test_search_component_names(self, tailwind_plus_instance):
        """Words in the dotted name match."""
        results = tailwind_plus_instance.search_component_names("Forms")

        assert sorted(result.full_name for result in results) == [
            "Application UI.Forms.Input Groups.Label with leading icon",
            "Application UI.Forms.Select Menus.Simple",
        ]

    def test_search_components_case_insensitive(self, tailwind_plus_instance):
        """Test that search is case insensitive."""
        results_lower = tailwind_plus_instance.search_component_names("breadcrumbs")
        results_upper = tailwind_plus_instance.search_component_names("BREADCRUMBS")

        assert results_lower == results_upper
        assert [result.full_name for result in results_lower] == [
            "Application UI.Navigation.Breadcrumbs.Simple"
        ]

    def test_search_components_no_match(self, tailwind_plus_instance):
        """Test searching with no matches."""
        assert tailwind_plus_instance.search_component_names("nonexistent") == []

    def test_explicit_data_file_path(self, sample_data, tmp_path):
        """Test that TailwindPlus loads data from explicitly provided file path."""
        test_file = tmp_path / "tailwindplus-components-test.json"

        with open(test_file, "w") as f:
            json.dump(sample_data, f)

        with TailwindPlus(str(test_file), cache_dir=str(tmp_path)) as instance:
            component_names = instance.list_component_names()
        expected_names = [
            "Application UI.Forms.Input Groups.Label with leading icon",
            "Application UI.Forms.Select Menus.Simple",
            "Application UI.Navigation.Breadcrumbs.Simple",
            "Ecommerce.Product Lists.Simple",
        ]
        assert all(name in component_names for name in expected_names)

    def test_list_tailwindplus_information(self, tailwind_plus_instance):
        """Test that list_tailwindplus_information returns metadata correctly."""
        info = tailwind_plus_instance.list_tailwindplus_information()

        assert isinstance(info, dict)
        assert info["version"] == "test-2025-07-15"
        assert info["downloaded_at"] == "2025-07-15T00:00:00.000Z"
        assert info["component_count"] == 4
        assert info["download_duration"] == "1.0s"
        assert info["downloader_version"] == "3.0.0"


class TestComponentSearch:
    """Test search across names, prose, parts and descriptions."""

    EMAIL_INPUT = "Application UI.Forms.Input Groups.Label with leading icon"
    BREADCRUMBS = "Application UI.Navigation.Breadcrumbs.Simple"

    def _names(self, results):
        return [result.full_name for result in results]

    def test_prose_match_returns_prose_and_parts(self, tailwind_plus_instance):
        [result] = tailwind_plus_instance.search_component_names("you@example")

        assert result.full_name == self.EMAIL_INPUT
        assert result.prose == ["Email", "you@example.com"]
        assert result.parts == ["envelope icon"]
        assert result.description is None

    def test_part_match(self, tailwind_plus_instance):
        results = tailwind_plus_instance.search_component_names("envelope")
        assert self._names(results) == [self.EMAIL_INPUT]

    def test_matched_description_is_returned(self, tailwind_plus_instance):
        [result] = tailwind_plus_instance.search_component_names("hierarchy")

        assert result.full_name == self.BREADCRUMBS
        assert result.description == (
            "Breadcrumb examples for Tailwind CSS. "
            "Show users where they are in a site hierarchy."
        )

    def test_description_comes_with_first_result_of_subcategory(
        self, sample_data, tmp_path
    ):
        """Components of a subcategory share its description, so it is returned
        once."""
        breadcrumbs = sample_data["tailwindplus"]["Application UI"]["Navigation"][
            "Breadcrumbs"
        ]
        breadcrumbs["With chevrons"] = {
            **breadcrumbs["Simple"],
            "name": "With chevrons",
        }
        path = tmp_path / "two-breadcrumbs.json"
        path.write_text(json.dumps(sample_data))

        with TailwindPlus(str(path), cache_dir=str(tmp_path)) as tailwind_plus:
            results = tailwind_plus.search_component_names("hierarchy")

        assert len(results) == 2
        assert results[0].description is not None
        assert results[1].description is None

    def test_unmatched_description_is_omitted(self, tailwind_plus_instance):
        [result] = tailwind_plus_instance.search_component_names("projects")

        assert result.full_name == self.BREADCRUMBS
        assert result.description is None

    def test_product_descriptions_are_not_searched(self, tailwind_plus_instance):
        assert tailwind_plus_instance.search_component_names("tables") == []

    def test_partial_and_stemmed_words(self, tailwind_plus_instance):
        assert self._names(
            tailwind_plus_instance.search_component_names("breadcr")
        ) == [self.BREADCRUMBS]
        assert self._names(tailwind_plus_instance.search_component_names("emails")) == [
            self.EMAIL_INPUT
        ]

    def test_all_words_before_any_word(self, tailwind_plus_instance):
        """Components matching every word win; without any, those matching some
        word are returned."""
        assert self._names(
            tailwind_plus_instance.search_component_names("email label")
        ) == [self.EMAIL_INPUT]
        assert sorted(
            self._names(tailwind_plus_instance.search_component_names("email projects"))
        ) == [self.EMAIL_INPUT, self.BREADCRUMBS]

    def test_limit(self, tailwind_plus_instance):
        assert (
            len(tailwind_plus_instance.search_component_names("simple", limit=1)) == 1
        )

    @pytest.mark.parametrize("limit", [0, MAX_SEARCH_RESULTS + 1])
    def test_limit_out_of_range(self, tailwind_plus_instance, limit):
        with pytest.raises(ValueError, match="limit must be between"):
            tailwind_plus_instance.search_component_names("simple", limit=limit)

    @pytest.mark.parametrize("search_term", ["", "  ", '"', 'email" OR *'])
    def test_query_syntax_is_searched_as_text(
        self, tailwind_plus_instance, search_term
    ):
        """Search terms are words, never FTS5 query syntax."""
        tailwind_plus_instance.search_component_names(search_term)

    def test_repeated_and_excess_words(self, tailwind_plus_instance):
        """Repeated words are searched once, and words past MAX_SEARCH_WORDS
        are ignored, so a long search term stays fast."""
        begun = time.perf_counter()
        results = tailwind_plus_instance.search_component_names("email " * 10_000)
        assert time.perf_counter() - begun < 0.5
        assert self._names(results) == [self.EMAIL_INPUT]

        unmatched = [f"zz{number}" for number in range(MAX_SEARCH_WORDS)]
        assert self._names(
            tailwind_plus_instance.search_component_names(
                " ".join(["email", *unmatched])
            )
        ) == [self.EMAIL_INPUT]
        assert (
            tailwind_plus_instance.search_component_names(
                " ".join([*unmatched, "email"])
            )
            == []
        )

    def test_long_prose_is_capped(self):
        fragment = "x" * (MAX_RESULT_PROSE_CHARS // 2)
        assert _capped_prose([fragment, fragment, fragment]) == [
            fragment,
            fragment,
            "…",
        ]

    def test_data_without_descriptions(self, sample_data, tmp_path):
        """Data files from downloaders before 4.0.0 have no descriptions."""
        del sample_data["descriptions"]
        path = tmp_path / "no-descriptions.json"
        path.write_text(json.dumps(sample_data))

        with TailwindPlus(str(path), cache_dir=str(tmp_path)) as tailwind_plus:
            results = tailwind_plus.search_component_names("projects")

        assert [result.description for result in results] == [None]


class TestCodeSearch:
    """Test finding the components code was copied from."""

    EMAIL_INPUT = "Application UI.Forms.Input Groups.Label with leading icon"
    SELECT_MENU = "Application UI.Forms.Select Menus.Simple"

    def _code(self, tailwind_plus_instance, full_name, framework=Framework.HTML):
        return tailwind_plus_instance.get_component_by_full_name(
            full_name, framework, TailwindVersion.V4, Mode.LIGHT
        ).code

    def test_component_code_matches_itself(self, tailwind_plus_instance):
        code = self._code(tailwind_plus_instance, self.SELECT_MENU)

        [first, *_] = tailwind_plus_instance.search_components_by_code(
            code, Framework.HTML
        )

        assert first == CodeMatch(
            full_name=self.SELECT_MENU,
            tailwind_version=TailwindVersion.V4,
            mode=Mode.LIGHT,
            similarity=1.0,
        )

    def test_edited_part_matches(self, tailwind_plus_instance):
        """The input of the email field, with its classes reordered and wrapped
        in a new element, still matches the email field first."""
        code = """<form class="space-y-4">
  <input type="email" class="sm:leading-6 sm:text-sm focus:ring-indigo-600 focus:ring-inset focus:ring-2 placeholder:text-gray-400 ring-gray-300 ring-inset ring-1 text-gray-900 pl-10 py-1.5 border-0 rounded-md w-full block">
</form>"""

        matches = tailwind_plus_instance.search_components_by_code(code, Framework.HTML)

        assert matches[0].full_name == self.EMAIL_INPUT
        assert matches[0].similarity < 1

    def test_framework_variants_only(self, tailwind_plus_instance):
        """React code is compared only with React variants."""
        code = self._code(tailwind_plus_instance, self.EMAIL_INPUT, Framework.REACT)

        matches = tailwind_plus_instance.search_components_by_code(
            code, Framework.REACT
        )

        assert [match.full_name for match in matches] == [self.EMAIL_INPUT]

    @pytest.mark.parametrize(
        "code", ["", "plain text", '<div class="unknown-class"></div>']
    )
    def test_code_sharing_nothing(self, tailwind_plus_instance, code):
        assert (
            tailwind_plus_instance.search_components_by_code(code, Framework.HTML) == []
        )

    def test_limit(self, tailwind_plus_instance):
        code = '<div class="block text-sm font-medium leading-6 text-gray-900"></div>'
        matches = tailwind_plus_instance.search_components_by_code(
            code, Framework.HTML, limit=1
        )
        assert len(matches) == 1

    @pytest.mark.parametrize("limit", [0, MAX_SEARCH_RESULTS + 1])
    def test_limit_out_of_range(self, tailwind_plus_instance, limit):
        with pytest.raises(ValueError, match="limit must be between"):
            tailwind_plus_instance.search_components_by_code(
                "<div></div>", Framework.HTML, limit=limit
            )


class TestSQLiteCache:
    """Test SQLite cache creation, reuse, and rebuild."""

    def test_parallel_build_matches_serial_build(
        self, data_file, tmp_path, monkeypatch
    ):
        """Code parsed in worker processes indexes the same as code parsed in
        the building process.

        Token ids follow the iteration order of token sets, which varies between
        processes, so tokens are compared by what they are.
        """
        queries = {
            "search": "SELECT * FROM component_search",
            "snippets": """
                SELECT full_name, framework, tailwind_version, mode,
                    ROUND(weight, 9)
                FROM structure_snippets
            """,
            "tokens": """
                SELECT framework, token, weight FROM structure_tokens
            """,
        }

        def token_snippets(db):
            """Each token with the snippets having it, by their variants."""
            variants = {
                row["id"]: (row["full_name"], row["tailwind_version"], row["mode"])
                for row in db.execute("SELECT * FROM structure_snippets")
            }
            for row in db.execute("SELECT * FROM structure_tokens"):
                snippet_ids = array(tailwind_plus._SNIPPET_ID_TYPECODE)
                snippet_ids.frombytes(row["snippet_ids"])
                for snippet_id in snippet_ids:
                    yield row["framework"], row["token"], *variants[snippet_id]

        def contents(cache_dir):
            with TailwindPlus(data_file, cache_dir=str(cache_dir)) as tailwind_plus:
                return {
                    "token snippets": sorted(token_snippets(tailwind_plus._db)),
                    **{
                        name: sorted(map(tuple, tailwind_plus._db.execute(query)))
                        for name, query in queries.items()
                    },
                }

        serial = contents(tmp_path / "serial")
        monkeypatch.setattr(tailwind_plus, "_PARALLEL_PARSING_MIN_SNIPPETS", 1)
        parallel = contents(tmp_path / "parallel")

        assert parallel == serial

    def test_build_removes_files_of_killed_builds(self, data_file, tmp_path):
        """A build killed before it could clean up leaves its partial file;
        the next build removes it."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache_path = TailwindPlus._get_cache_path(data_file, str(cache_dir))
        killed_build = cache_dir / f"{os.path.basename(cache_path)}.x1y2z3.building"
        killed_build.write_bytes(b"partial")

        TailwindPlus(data_file, cache_dir=str(cache_dir)).close()

        assert not killed_build.exists()
        assert os.path.exists(cache_path)

    def test_build_removes_stale_caches(self, sample_data, tmp_path):
        """A build removes the caches of data files that are gone or have
        changed, and keeps those of unchanged data files."""
        cache_dir = str(tmp_path / "cache")
        data_files = {}
        for name in ("gone", "changed", "unchanged", "current"):
            data_files[name] = tmp_path / f"{name}.json"
            data_files[name].write_text(json.dumps(sample_data))
        for name in ("gone", "changed", "unchanged"):
            TailwindPlus(str(data_files[name]), cache_dir=cache_dir).close()
        data_files["gone"].unlink()
        data_files["changed"].write_text(json.dumps(sample_data) + " ")

        TailwindPlus(str(data_files["current"]), cache_dir=cache_dir).close()

        def cache_exists(name):
            return os.path.exists(
                TailwindPlus._get_cache_path(str(data_files[name]), cache_dir)
            )

        assert not cache_exists("gone")
        assert not cache_exists("changed")
        assert cache_exists("unchanged")
        assert cache_exists("current")

    def test_servers_starting_at_once_build_once(
        self, data_file, tmp_path, monkeypatch
    ):
        """Instances created at once with a stale cache build it once; the
        others wait for it and open it."""
        build_cache = TailwindPlus._build_cache
        builds = []
        both_started = threading.Barrier(2)

        def slow_build_cache(self, *args):
            builds.append(threading.get_ident())
            # Give the other instance time to find the cache stale and wait.
            time.sleep(0.3)
            build_cache(self, *args)

        def start():
            both_started.wait()
            with TailwindPlus(data_file, cache_dir=str(tmp_path / "cache")) as tp:
                return tp.list_component_names()

        monkeypatch.setattr(TailwindPlus, "_build_cache", slow_build_cache)
        with ThreadPoolExecutor(max_workers=2) as pool:
            names = list(pool.map(lambda _: start(), range(2)))

        assert len(builds) == 1
        assert names[0] == names[1] != []

    @pytest.mark.parametrize("failure", ["cannot start", "breaks", "breaks partway"])
    def test_build_without_workers(
        self, data_file, tmp_path, monkeypatch, caplog, failure
    ):
        """When worker processes cannot start, or fail while parsing, code is
        parsed in the building process instead, from where the workers
        stopped."""
        with TailwindPlus(data_file, cache_dir=str(tmp_path / "serial")) as serial:
            expected = serial.search_components_by_code(
                serial.get_component_by_full_name(
                    TestCodeSearch.EMAIL_INPUT,
                    Framework.HTML,
                    TailwindVersion.V4,
                    Mode.LIGHT,
                ).code,
                Framework.HTML,
            )

        class FailingPool:
            def __init__(self, *args, **kwargs):
                pass

            def map(self, function, *iterables, chunksize=1):
                if failure == "cannot start":
                    raise BlockingIOError(35, "Resource temporarily unavailable")

                def broken():
                    if failure == "breaks partway":
                        yield function(*next(zip(*iterables, strict=True)))
                    raise BrokenProcessPool("a worker died")

                return broken()

            def shutdown(self, **kwargs):
                pass

        monkeypatch.setattr(tailwind_plus, "ProcessPoolExecutor", FailingPool)
        monkeypatch.setattr(tailwind_plus, "_PARALLEL_PARSING_MIN_SNIPPETS", 1)
        with TailwindPlus(data_file, cache_dir=str(tmp_path / "cache")) as tp:
            code = tp.get_component_by_full_name(
                TestCodeSearch.EMAIL_INPUT,
                Framework.HTML,
                TailwindVersion.V4,
                Mode.LIGHT,
            ).code
            assert tp.search_components_by_code(code, Framework.HTML) == expected
            assert tp.search_component_names("you@example")

        assert "Parsing component code in this process" in caplog.text

    def test_interrupted_build_leaves_no_cache(self, data_file, tmp_path, monkeypatch):
        """A build that fails leaves neither a cache nor its partial file, only
        the lock file that every build uses."""

        def fail(*args):
            raise RuntimeError("build interrupted")

        monkeypatch.setattr(TailwindPlus, "_index_structure", fail)
        with pytest.raises(RuntimeError, match="build interrupted"):
            TailwindPlus(data_file, cache_dir=str(tmp_path / "cache"))

        assert [path.suffix for path in (tmp_path / "cache").iterdir()] == [".lock"]

    def test_cache_file_is_created(self, data_file, tmp_path):
        """Test that a cache DB file is created on first instantiation."""
        cache_dir = str(tmp_path / "cache")
        cache_path = TailwindPlus._get_cache_path(data_file, cache_dir)
        import os

        assert not os.path.exists(cache_path)

        TailwindPlus(data_file, cache_dir=cache_dir).close()

        assert os.path.exists(cache_path)

    def test_context_manager_closes_connection(self, data_file, tmp_path):
        """The context manager yields a usable instance and closes it on exit."""
        with TailwindPlus(data_file, cache_dir=str(tmp_path)) as tp:
            assert tp.list_component_names()

        with pytest.raises(sqlite3.ProgrammingError):
            tp._db.execute("SELECT 1")

    def test_concurrent_reads(self, tailwind_plus_instance):
        """Calls from many threads at once, as FastMCP makes them, return what
        the same calls return one at a time."""
        calls = [
            (full_name, framework)
            for full_name in [
                "Application UI.Forms.Input Groups.Label with leading icon",
                "Application UI.Forms.Select Menus.Simple",
                "Application UI.Navigation.Breadcrumbs.Simple",
            ]
            for framework in (Framework.HTML, Framework.REACT)
        ] * 100

        def get(call):
            full_name, framework = call
            try:
                return tailwind_plus_instance.get_component_by_full_name(
                    full_name, framework, TailwindVersion.V4, Mode.LIGHT
                ).code
            except Exception as error:
                return type(error).__name__

        one_at_a_time = [get(call) for call in calls]
        with ThreadPoolExecutor(max_workers=16) as pool:
            concurrently = list(pool.map(get, calls))

        assert concurrently == one_at_a_time

    def test_connection_is_read_only(self, tailwind_plus_instance):
        """The cache connection rejects writes but still serves reads."""
        with pytest.raises(sqlite3.OperationalError):
            tailwind_plus_instance._db.execute("CREATE TABLE should_not_exist (x)")

        assert tailwind_plus_instance.list_component_names()

    def test_cache_is_reused(self, data_file, tmp_path):
        """Test that second instantiation reuses the cache (no re-parse)."""
        import os

        cache_dir = str(tmp_path / "cache")

        # First instantiation builds the cache
        TailwindPlus(data_file, cache_dir=cache_dir).close()
        cache_path = TailwindPlus._get_cache_path(data_file, cache_dir)
        first_mtime = os.stat(cache_path).st_mtime

        # Second instantiation should reuse
        with TailwindPlus(data_file, cache_dir=cache_dir) as instance2:
            second_mtime = os.stat(cache_path).st_mtime

            assert first_mtime == second_mtime
            assert instance2.version == "test-2025-07-15"
            assert len(instance2.list_component_names()) == 4

    def test_cache_rebuilds_on_data_change(self, sample_data, data_file, tmp_path):
        """Test that modified data file triggers cache rebuild."""
        import os
        import time

        cache_dir = str(tmp_path / "cache")

        # First instantiation builds the cache
        TailwindPlus(data_file, cache_dir=cache_dir).close()
        cache_path = TailwindPlus._get_cache_path(data_file, cache_dir)
        first_mtime = os.stat(cache_path).st_mtime

        # Modify the data file (change version)
        time.sleep(0.05)  # Ensure filesystem mtime changes
        sample_data["version"] = "test-2025-07-16-updated"
        with open(data_file, "w") as f:
            json.dump(sample_data, f)

        # Second instantiation should rebuild cache
        with TailwindPlus(data_file, cache_dir=cache_dir) as instance2:
            second_mtime = os.stat(cache_path).st_mtime

            assert second_mtime > first_mtime
            assert instance2.version == "test-2025-07-16-updated"

    def test_cache_staleness_detects_size_change(
        self, sample_data, data_file, tmp_path
    ):
        """Test that cache detects file size changes."""
        cache_dir = str(tmp_path / "cache")

        TailwindPlus(data_file, cache_dir=cache_dir).close()
        cache_path = TailwindPlus._get_cache_path(data_file, cache_dir)

        # The cache should not be stale
        assert not TailwindPlus._cache_is_stale(cache_path, data_file)

        # Write different-sized content (add extra whitespace to change size)
        with open(data_file, "w") as f:
            json.dump(sample_data, f, indent=4)

        # Now cache should be stale due to size change
        assert TailwindPlus._cache_is_stale(cache_path, data_file)

    def test_cache_from_older_format_is_stale(self, data_file, tmp_path):
        """A cache built before the current cache format is rebuilt."""
        cache_dir = str(tmp_path / "cache")
        TailwindPlus(data_file, cache_dir=cache_dir).close()
        cache_path = TailwindPlus._get_cache_path(data_file, cache_dir)

        db = sqlite3.connect(cache_path)
        db.execute("DELETE FROM metadata WHERE key = 'cache_format'")
        db.commit()
        db.close()

        assert TailwindPlus._cache_is_stale(cache_path, data_file)

    def test_missing_cache_is_stale(self, data_file):
        """Test that a non-existent cache path is considered stale."""
        assert TailwindPlus._cache_is_stale("/nonexistent/path.db", data_file)


class TestErrorHandling:
    """Test error handling and suggestions functionality."""

    def test_component_not_found_error_raised(self, tailwind_plus_instance):
        """Test that ComponentNotFoundError is raised for non-existent components."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "nonexistent.component", Framework.HTML, TailwindVersion.V4, Mode.LIGHT
            )

        assert exc_info.value.component_name == "nonexistent.component"
        assert "Component `nonexistent.component` not found" in str(exc_info.value)

    def test_suggestions_for_component_name(self, tailwind_plus_instance):
        """Test the suggestions helper function."""
        # Test with a partial match that should find suggestions
        suggestions = tailwind_plus_instance._suggestions_for_component_name("Forms")
        assert len(suggestions) > 0
        assert all("Forms" in suggestion for suggestion in suggestions)

        # Test with no matches
        suggestions = tailwind_plus_instance._suggestions_for_component_name(
            "nonexistent"
        )
        assert len(suggestions) == 0

        # Test max_suggestions parameter
        suggestions = tailwind_plus_instance._suggestions_for_component_name(
            "Application", max_suggestions=2
        )
        assert len(suggestions) <= 2

    def test_suggestions_included_in_error(self, tailwind_plus_instance):
        """Test that suggestions are included in ComponentNotFoundError."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Application.Forms.Input",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.LIGHT,
            )

        error = exc_info.value
        assert error.component_name == "Application.Forms.Input"
        assert len(error.suggestions) > 0
        assert "Did you mean one of:" in str(error)

        # Verify suggestions contain relevant components
        suggestions_text = str(error)
        assert any(
            "Forms" in suggestions_text or "Application" in suggestions_text
            for _ in [True]
        )

    def test_suggestions_with_exact_partial_matches(self, tailwind_plus_instance):
        """Test suggestions work with exact partial component name matches."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Application UI.Forms.Wrong Name",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.LIGHT,
            )

        error = exc_info.value
        # Should suggest components that contain "Application UI" and "Forms"
        suggestions = error.suggestions
        assert len(suggestions) > 0
        assert any("Application UI.Forms" in suggestion for suggestion in suggestions)

    def test_no_suggestions_for_completely_invalid_name(self, tailwind_plus_instance):
        """Test that completely invalid names don't get suggestions."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "xyz.abc.def", Framework.HTML, TailwindVersion.V4, Mode.LIGHT
            )

        error = exc_info.value
        # Should have no suggestions for completely unrelated names
        assert len(error.suggestions) == 0
        assert "Did you mean" not in str(error)

    def test_get_component_preview_by_full_name(self, tailwind_plus_instance):
        """Test getting component preview."""
        preview = tailwind_plus_instance.get_component_preview_by_full_name(
            "Application UI.Forms.Input Groups.Label with leading icon",
            Framework.HTML,
            TailwindVersion.V4,
            Mode.LIGHT,
        )

        assert isinstance(preview, str)
        assert "Email input preview" in preview

    def test_get_component_preview_by_full_name_not_exists(
        self, tailwind_plus_instance
    ):
        """Test getting preview for non-existent component."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_preview_by_full_name(
                "nonexistent.component", Framework.HTML, TailwindVersion.V4, Mode.LIGHT
            )

        assert exc_info.value.component_name == "nonexistent.component"

    def test_get_component_react_variant(self, tailwind_plus_instance):
        """Test getting React variant of a component."""
        result = tailwind_plus_instance.get_component_by_full_name(
            "Application UI.Forms.Input Groups.Label with leading icon",
            Framework.REACT,
            TailwindVersion.V4,
            Mode.LIGHT,
        )

        assert result.framework == Framework.REACT
        assert result.language == Language.JSX
        assert (
            "Email input React preview"
            in tailwind_plus_instance.get_component_preview_by_full_name(
                "Application UI.Forms.Input Groups.Label with leading icon",
                Framework.REACT,
                TailwindVersion.V4,
                Mode.LIGHT,
            )
        )


class TestComponentNameLevels:
    """Test listing the name levels below a parent."""

    @pytest.mark.parametrize(
        ("parent_levels", "expected"),
        [
            ([], ["Application UI", "Ecommerce"]),
            (["Application UI"], ["Forms", "Navigation"]),
            (["Application UI", "Forms"], ["Input Groups", "Select Menus"]),
            (["Application UI", "Forms", "Select Menus"], ["Simple"]),
            (["Marketing"], []),
        ],
    )
    def test_levels_below_parent(self, tailwind_plus_instance, parent_levels, expected):
        assert tailwind_plus_instance.component_name_levels(parent_levels) == expected


class TestModeValidation:
    """Test mode validation logic for eCommerce vs non-eCommerce components."""

    def test_modes_for_product(self):
        """eCommerce components support only 'none'; all others support the
        three themed modes."""
        assert TailwindPlus.modes_for_product("Ecommerce") == [Mode.NONE]
        assert TailwindPlus.modes_for_product("Marketing") == [
            Mode.LIGHT,
            Mode.DARK,
            Mode.SYSTEM,
        ]

    def test_ecommerce_component_with_valid_mode(self, tailwind_plus_instance):
        """Test that eCommerce components work with Mode.NONE."""
        component = tailwind_plus_instance.get_component_by_full_name(
            "Ecommerce.Product Lists.Simple",
            Framework.HTML,
            TailwindVersion.V4,
            Mode.NONE,
        )

        assert component.mode == Mode.NONE
        assert component.full_name == "Ecommerce.Product Lists.Simple"
        assert (
            "Product list preview"
            in tailwind_plus_instance.get_component_preview_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.NONE,
            )
        )

    def test_ecommerce_component_with_invalid_mode_light(self, tailwind_plus_instance):
        """Test that eCommerce components reject Mode.LIGHT."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.LIGHT,
            )

        error_msg = str(exc_info.value)
        assert (
            "eCommerce component 'Ecommerce.Product Lists.Simple' must use mode='none'"
            in error_msg
        )
        assert "Got mode='light'" in error_msg
        assert "eCommerce components only support mode='none'" in error_msg

    def test_ecommerce_component_with_invalid_mode_dark(self, tailwind_plus_instance):
        """Test that eCommerce components reject Mode.DARK."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.DARK,
            )

        error_msg = str(exc_info.value)
        assert (
            "eCommerce component 'Ecommerce.Product Lists.Simple' must use mode='none'"
            in error_msg
        )
        assert "Got mode='dark'" in error_msg
        assert "eCommerce components only support mode='none'" in error_msg

    def test_ecommerce_component_with_invalid_mode_system(self, tailwind_plus_instance):
        """Test that eCommerce components reject Mode.SYSTEM."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.SYSTEM,
            )

        error_msg = str(exc_info.value)
        assert (
            "eCommerce component 'Ecommerce.Product Lists.Simple' must use mode='none'"
            in error_msg
        )
        assert "Got mode='system'" in error_msg
        assert "eCommerce components only support mode='none'" in error_msg

    def test_non_ecommerce_component_with_invalid_mode(self, tailwind_plus_instance):
        """Test that non-eCommerce components reject Mode.NONE."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Application UI.Forms.Input Groups.Label with leading icon",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.NONE,
            )

        error_msg = str(exc_info.value)
        assert (
            "Component 'Application UI.Forms.Input Groups.Label with leading icon' cannot use mode='none'"
            in error_msg
        )
        assert "Got mode='none'" in error_msg
        assert (
            "Application UI and Marketing components support modes: 'light', 'dark', 'system'"
            in error_msg
        )

    def test_ecommerce_preview_with_invalid_mode(self, tailwind_plus_instance):
        """Test that eCommerce preview components reject non-NONE modes."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_preview_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.LIGHT,
            )

        error_msg = str(exc_info.value)
        assert (
            "eCommerce component 'Ecommerce.Product Lists.Simple' must use mode='none'"
            in error_msg
        )
        assert "Got mode='light'" in error_msg
        assert "eCommerce components only support mode='none'" in error_msg

    def test_non_ecommerce_preview_with_invalid_mode(self, tailwind_plus_instance):
        """Test that non-eCommerce preview components reject Mode.NONE."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_preview_by_full_name(
                "Application UI.Forms.Input Groups.Label with leading icon",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.NONE,
            )

        error_msg = str(exc_info.value)
        assert (
            "Component 'Application UI.Forms.Input Groups.Label with leading icon' cannot use mode='none'"
            in error_msg
        )
        assert "Got mode='none'" in error_msg
        assert (
            "Application UI and Marketing components support modes: 'light', 'dark', 'system'"
            in error_msg
        )


class TestErrorMessageConsistency:
    """Test that error messages are consistent across different methods and client-friendly."""

    def test_error_message_format_contains_client_friendly_strings(
        self, tailwind_plus_instance
    ):
        """Test that error messages contain client-friendly 'mode=' format."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.LIGHT,
            )

        error_msg = str(exc_info.value)
        assert "mode='none'" in error_msg
        assert "mode='light'" in error_msg
        assert "Mode.NONE" not in error_msg  # Should not contain enum representation

    def test_preview_and_main_method_consistent_error_messages(
        self, tailwind_plus_instance
    ):
        """Test that preview and main methods have consistent error messages."""
        # Test main method
        with pytest.raises(ValueError) as main_exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.SYSTEM,
            )

        # Test preview method
        with pytest.raises(ValueError) as preview_exc_info:
            tailwind_plus_instance.get_component_preview_by_full_name(
                "Ecommerce.Product Lists.Simple",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.SYSTEM,
            )

        main_error = str(main_exc_info.value)
        preview_error = str(preview_exc_info.value)

        # Both should have the same format
        # Both should have the same format with improved error messages
        assert (
            "eCommerce component 'Ecommerce.Product Lists.Simple' must use mode='none'"
            in main_error
        )
        assert "Got mode='system'" in main_error
        assert "eCommerce components only support mode='none'" in main_error

        assert (
            "eCommerce component 'Ecommerce.Product Lists.Simple' must use mode='none'"
            in preview_error
        )
        assert "Got mode='system'" in preview_error
        assert "eCommerce components only support mode='none'" in preview_error

    def test_all_validation_paths_use_client_friendly_format(
        self, tailwind_plus_instance
    ):
        """Test that all validation error paths use client-friendly mode format."""
        test_cases = [
            # (method, component_name, args, expected_mode_in_error)
            (
                "get_component_by_full_name",
                "Ecommerce.Product Lists.Simple",
                (Framework.HTML, TailwindVersion.V4, Mode.DARK),
                "dark",
            ),
            (
                "get_component_preview_by_full_name",
                "Ecommerce.Product Lists.Simple",
                (Framework.HTML, TailwindVersion.V4, Mode.LIGHT),
                "light",
            ),
        ]

        for method_name, component_name, args, expected_mode in test_cases:
            method = getattr(tailwind_plus_instance, method_name)

            with pytest.raises(ValueError) as exc_info:
                method(component_name, *args)

            error_msg = str(exc_info.value)

            # All should use client-friendly format
            assert "mode='none'" in error_msg
            assert f"mode='{expected_mode}'" in error_msg
            assert "Mode.NONE" not in error_msg  # No enum representation
            assert "Mode.LIGHT" not in error_msg
            assert "Mode.DARK" not in error_msg
            assert "Mode.SYSTEM" not in error_msg
