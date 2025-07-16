import json
from io import StringIO

import pytest

from mcp_tailwindplus.tailwind_plus import (
    Component,
    ComponentNotFoundError,
    Framework,
    Language,
    Mode,
    TailwindPlus,
    TailwindVersion,
)


@pytest.fixture
def sample_data():
    """Fragment of real TailwindPlus component data for testing with new format."""
    return {
        "version": "test-2025-07-15",
        "downloaded_at": "2025-07-15T00:00:00.000Z",
        "component_count": 3,
        "download_duration": "1.0s",
        "downloader_version": "2.0.0",
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
                                    "code": """<div>
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
            }
        },
    }


@pytest.fixture
def tailwind_plus_instance(sample_data):
    """Create a TailwindPlus instance with test data using StringIO."""
    test_data_io = StringIO(json.dumps(sample_data))
    return TailwindPlus(test_data_io)


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
        ]

        paths = tailwind_plus_instance.list_component_names()
        assert sorted(paths) == sorted(expected_paths)

    def test_list_component_names(self, tailwind_plus_instance):
        """Test listing all component names."""
        names = tailwind_plus_instance.list_component_names()

        assert isinstance(names, list)
        assert len(names) == 3
        assert "Application UI.Forms.Input Groups.Label with leading icon" in names
        assert "Application UI.Forms.Select Menus.Simple" in names
        assert "Application UI.Navigation.Breadcrumbs.Simple" in names

    def test_get_component_by_full_name_exists(self, tailwind_plus_instance):
        """Test getting an existing component by full name."""
        result = tailwind_plus_instance.get_component_by_full_name(
            "Application UI.Forms.Input Groups.Label with leading icon",
            Framework.HTML,
            TailwindVersion.V4,
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
                "nonexistent.component", Framework.HTML, TailwindVersion.V4
            )

        assert exc_info.value.component_name == "nonexistent.component"

    def test_search_component_names(self, tailwind_plus_instance):
        """Test searching for component names."""
        # Search for "Forms" should return form-related components
        results = tailwind_plus_instance.search_component_names("Forms")

        assert isinstance(results, list)
        assert len(results) == 2  # Label with leading icon and Simple
        assert all("Forms" in name for name in results)

    def test_search_components_case_insensitive(self, tailwind_plus_instance):
        """Test that search is case insensitive."""
        results_lower = tailwind_plus_instance.search_component_names("breadcrumbs")
        results_upper = tailwind_plus_instance.search_component_names("BREADCRUMBS")

        assert results_lower == results_upper
        assert len(results_lower) == 1
        assert "Application UI.Navigation.Breadcrumbs.Simple" in results_lower

    def test_search_components_no_match(self, tailwind_plus_instance):
        """Test searching with no matches."""
        results = tailwind_plus_instance.search_component_names("nonexistent")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_explicit_data_file_path(self, sample_data, tmp_path):
        """Test that TailwindPlus loads data from explicitly provided file path."""
        # Use pytest's tmp_path fixture to create a proper temporary file
        test_file = tmp_path / "tailwindplus-components-test.json"

        with open(test_file, "w") as f:
            json.dump(sample_data, f)

        # Create instance with explicit file path
        instance = TailwindPlus(str(test_file))
        # Test that components were loaded correctly
        component_names = instance.list_component_names()
        expected_names = [
            "Application UI.Forms.Input Groups.Label with leading icon",
            "Application UI.Forms.Select Menus.Simple",
            "Application UI.Navigation.Breadcrumbs.Simple",
        ]
        assert all(name in component_names for name in expected_names)

        # tmp_path automatically cleans up


class TestErrorHandling:
    """Test error handling and suggestions functionality."""

    def test_component_not_found_error_raised(self, tailwind_plus_instance):
        """Test that ComponentNotFoundError is raised for non-existent components."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "nonexistent.component", Framework.HTML, TailwindVersion.V4
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
                "Application.Forms.Input", Framework.HTML, TailwindVersion.V4
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
                "Application UI.Forms.Wrong Name", Framework.HTML, TailwindVersion.V4
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
                "xyz.abc.def", Framework.HTML, TailwindVersion.V4
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
        )

        assert isinstance(preview, str)
        assert "Email input preview" in preview

    def test_get_component_preview_by_full_name_not_exists(
        self, tailwind_plus_instance
    ):
        """Test getting preview for non-existent component."""
        with pytest.raises(ComponentNotFoundError) as exc_info:
            tailwind_plus_instance.get_component_preview_by_full_name(
                "nonexistent.component", Framework.HTML, TailwindVersion.V4
            )

        assert exc_info.value.component_name == "nonexistent.component"

    def test_get_component_react_variant(self, tailwind_plus_instance):
        """Test getting React variant of a component."""
        result = tailwind_plus_instance.get_component_by_full_name(
            "Application UI.Forms.Input Groups.Label with leading icon",
            Framework.REACT,
            TailwindVersion.V4,
        )

        assert result.framework == Framework.REACT
        assert result.language == Language.JSX
        assert (
            "Email input React preview"
            in tailwind_plus_instance.get_component_preview_by_full_name(
                "Application UI.Forms.Input Groups.Label with leading icon",
                Framework.REACT,
                TailwindVersion.V4,
            )
        )
