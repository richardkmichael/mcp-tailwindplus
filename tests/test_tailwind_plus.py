import json
import os
from io import StringIO
from unittest.mock import patch

import pytest

from mcp_tailwindui.tailwind_plus import TailwindPlus


@pytest.fixture
def sample_data():
    """Fragment of real TailwindUI component data for testing."""
    return {
        "application_ui": {
            "forms": {
                "input_groups": {
                    "label_with_leading_icon": """<div>
  <label for="email" class="block text-sm font-medium leading-6 text-gray-900">Email</label>
  <div class="relative mt-2 rounded-md shadow-sm">
    <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
      <svg class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path d="M3 4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2-2V4z" />
      </svg>
    </div>
    <input type="email" name="email" id="email" class="block w-full rounded-md border-0 py-1.5 pl-10 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6" placeholder="you@example.com">
  </div>
</div>"""
                },
                "select_menus": {
                    "simple": """<div>
  <label for="location" class="block text-sm font-medium leading-6 text-gray-900">Location</label>
  <select id="location" name="location" class="mt-2 block w-full rounded-md border-0 py-1.5 pl-3 pr-10 text-gray-900 ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-indigo-600 sm:text-sm sm:leading-6">
    <option>United States</option>
    <option>Canada</option>
    <option>Mexico</option>
  </select>
</div>"""
                },
            },
            "navigation": {
                "breadcrumbs": {
                    "simple": """<nav class="flex" aria-label="Breadcrumb">
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
</nav>"""
                }
            },
        }
    }


@pytest.fixture
def tailwind_plus_instance(sample_data):
    """Create a TailwindPlus instance with test data using StringIO."""
    test_data_io = StringIO(json.dumps(sample_data))
    return TailwindPlus(test_data_io)


class TestTailwindPlus:
    def test_init_loads_data(self, tailwind_plus_instance, sample_data):
        """Test that initialization loads data correctly."""
        assert tailwind_plus_instance.data == sample_data
        assert len(tailwind_plus_instance._component_names) > 0

    def test_get_component_paths(self, tailwind_plus_instance):
        """Test that component paths are extracted correctly."""
        expected_paths = [
            "application_ui.forms.input_groups.label_with_leading_icon",
            "application_ui.forms.select_menus.simple",
            "application_ui.navigation.breadcrumbs.simple",
        ]

        paths = tailwind_plus_instance._component_names
        assert sorted(paths) == sorted(expected_paths)

    def test_list_component_names(self, tailwind_plus_instance):
        """Test listing all component names."""
        names = tailwind_plus_instance.list_component_names()

        assert isinstance(names, list)
        assert len(names) == 3
        assert "application_ui.forms.input_groups.label_with_leading_icon" in names
        assert "application_ui.forms.select_menus.simple" in names
        assert "application_ui.navigation.breadcrumbs.simple" in names

    def test_get_component_by_name_exists(self, tailwind_plus_instance):
        """Test getting an existing component by name."""
        result = tailwind_plus_instance.get_component_by_name(
            "application_ui.forms.input_groups.label_with_leading_icon"
        )

        assert isinstance(result, dict)
        assert "application_ui.forms.input_groups.label_with_leading_icon" in result
        component_data = result[
            "application_ui.forms.input_groups.label_with_leading_icon"
        ]
        assert isinstance(component_data, str)
        assert "Email" in component_data

    def test_get_component_by_name_not_exists(self, tailwind_plus_instance):
        """Test getting a non-existent component by name."""
        result = tailwind_plus_instance.get_component_by_name("nonexistent.component")

        assert isinstance(result, dict)
        assert "nonexistent.component" in result
        assert result["nonexistent.component"] == {}

    def test_search_components_by_name(self, tailwind_plus_instance):
        """Test searching components by name."""
        # Search for "forms" should return form-related components
        results = tailwind_plus_instance.search_components_by_name("forms")

        assert isinstance(results, list)
        assert len(results) == 2  # input_groups and select_menus
        assert all("forms" in name for name in results)

    def test_search_components_case_insensitive(self, tailwind_plus_instance):
        """Test that search is case insensitive."""
        results_lower = tailwind_plus_instance.search_components_by_name("breadcrumbs")
        results_upper = tailwind_plus_instance.search_components_by_name("BREADCRUMBS")

        assert results_lower == results_upper
        assert len(results_lower) == 1
        assert "application_ui.navigation.breadcrumbs.simple" in results_lower

    def test_search_components_no_match(self, tailwind_plus_instance):
        """Test searching with no matches."""
        results = tailwind_plus_instance.search_components_by_name("nonexistent")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_get_by_path_deep_nesting(self, tailwind_plus_instance):
        """Test getting component data from deeply nested path."""
        result = tailwind_plus_instance._get_by_path(
            "application_ui.forms.select_menus.simple"
        )

        assert isinstance(result, str)
        assert "Location" in result

    def test_get_by_path_invalid_path(self, tailwind_plus_instance):
        """Test getting component data with invalid path."""
        result = tailwind_plus_instance._get_by_path("invalid.path.here")

        assert result == {}

    def test_default_data_file_path(self, sample_data):
        """Test that default data file path is used when env var not set."""
        # Create a temporary file at the default location
        os.makedirs("tmp", exist_ok=True)
        default_file = "tmp/tailwindplus-components-2025-06-10-221317.json"

        try:
            with open(default_file, "w") as f:
                json.dump(sample_data, f)

            # Ensure env var is not set
            with patch.dict(os.environ, {}, clear=True):
                instance = TailwindPlus()
                assert instance.data == sample_data

        finally:
            # Cleanup
            if os.path.exists(default_file):
                os.unlink(default_file)
            if os.path.exists("tmp") and not os.listdir("tmp"):
                os.rmdir("tmp")
