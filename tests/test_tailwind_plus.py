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
        "component_count": 4,
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
            "Ecommerce.Product Lists.Simple",
        ]
        assert all(name in component_names for name in expected_names)

        # tmp_path automatically cleans up

    def test_list_tailwindplus_information(self, tailwind_plus_instance):
        """Test that list_tailwindplus_information returns metadata correctly."""
        info = tailwind_plus_instance.list_tailwindplus_information()

        assert isinstance(info, dict)
        assert info["version"] == "test-2025-07-15"
        assert info["downloaded_at"] == "2025-07-15T00:00:00.000Z"
        assert info["component_count"] == 4
        assert info["download_duration"] == "1.0s"
        assert info["downloader_version"] == "2.0.0"


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


class TestResourceAdapterMethods:
    """Test the resource adapter methods."""

    def test_get_component_as_resource(self, tailwind_plus_instance):
        """Test getting component via resource adapter method."""
        component = tailwind_plus_instance.get_component_as_resource(
            "Application UI.Forms.Input Groups.Label with leading icon",
            "html",
            "4",
            "light",
        )

        assert isinstance(component, Component)
        assert (
            component.full_name
            == "Application UI.Forms.Input Groups.Label with leading icon"
        )
        assert component.framework == Framework.HTML
        assert component.tailwind_version == TailwindVersion.V4
        assert "Email" in component.code

    def test_get_component_as_resource_react(self, tailwind_plus_instance):
        """Test getting React component via resource adapter method."""
        component = tailwind_plus_instance.get_component_as_resource(
            "Application UI.Forms.Input Groups.Label with leading icon",
            "react",
            "4",
            "light",
        )

        assert component.framework == Framework.REACT
        assert component.language == Language.JSX

    def test_get_component_preview_as_resource(self, tailwind_plus_instance):
        """Test getting component preview via resource adapter method."""
        preview = tailwind_plus_instance.get_component_preview_as_resource(
            "Application UI.Forms.Input Groups.Label with leading icon",
            "html",
            "4",
            "light",
        )

        assert isinstance(preview, str)
        assert "Email input preview" in preview

    def test_get_component_as_resource_invalid_framework(self, tailwind_plus_instance):
        """Test error handling for invalid framework."""
        with pytest.raises(ValueError):
            tailwind_plus_instance.get_component_as_resource(
                "Application UI.Forms.Input Groups.Label with leading icon",
                "invalidframework",
                "4",
                "light",
            )

    def test_get_component_as_resource_invalid_version(self, tailwind_plus_instance):
        """Test error handling for invalid version."""
        with pytest.raises(ValueError):
            tailwind_plus_instance.get_component_as_resource(
                "Application UI.Forms.Input Groups.Label with leading icon",
                "html",
                "99",
                "light",
            )

    def test_get_component_as_resource_nonexistent_component(
        self, tailwind_plus_instance
    ):
        """Test error handling for nonexistent component."""
        with pytest.raises(ComponentNotFoundError):
            tailwind_plus_instance.get_component_as_resource(
                "Application UI.Forms.Nonexistent Component", "html", "4", "light"
            )

    def test_get_component_preview_as_resource_nonexistent_component(
        self, tailwind_plus_instance
    ):
        """Test error handling for nonexistent component preview."""
        with pytest.raises(ComponentNotFoundError):
            tailwind_plus_instance.get_component_preview_as_resource(
                "Application UI.Forms.Nonexistent Component", "html", "4", "light"
            )

    def test_direct_component_name_usage(self, tailwind_plus_instance):
        """Test that resource adapter uses component names directly."""
        # Resource adapter should accept dot-separated component names directly
        component1 = tailwind_plus_instance.get_component_as_resource(
            "Application UI.Forms.Input Groups.Label with leading icon",
            "html",
            "4",
            "light",
        )

        # Compare with direct method call using dot notation
        component2 = tailwind_plus_instance.get_component_by_full_name(
            "Application UI.Forms.Input Groups.Label with leading icon",
            Framework.HTML,
            TailwindVersion.V4,
            Mode.LIGHT,
        )

        # Should be identical
        assert component1.full_name == component2.full_name
        assert component1.code == component2.code
        assert component1.framework == component2.framework


class TestModeValidation:
    """Test mode validation logic for eCommerce vs non-eCommerce components."""

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

    def test_ecommerce_resource_with_invalid_mode(self, tailwind_plus_instance):
        """Test that eCommerce resource adapter rejects invalid modes."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_as_resource(
                "Ecommerce.Product Lists.Simple",
                "html",
                "4",
                "light",
            )

        error_msg = str(exc_info.value)
        assert (
            "eCommerce component 'Ecommerce.Product Lists.Simple' must use mode='none'"
            in error_msg
        )
        assert "Got mode='light'" in error_msg
        assert "eCommerce components only support mode='none'" in error_msg

    def test_non_ecommerce_resource_with_invalid_mode(self, tailwind_plus_instance):
        """Test that non-eCommerce resource adapter rejects Mode.NONE."""
        with pytest.raises(ValueError) as exc_info:
            tailwind_plus_instance.get_component_as_resource(
                "Application UI.Forms.Input Groups.Label with leading icon",
                "html",
                "4",
                "none",
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

    def test_resource_and_main_method_consistent_error_messages(
        self, tailwind_plus_instance
    ):
        """Test that resource and main methods have consistent error message format."""
        # Test main method
        with pytest.raises(ValueError) as main_exc_info:
            tailwind_plus_instance.get_component_by_full_name(
                "Application UI.Forms.Input Groups.Label with leading icon",
                Framework.HTML,
                TailwindVersion.V4,
                Mode.NONE,
            )

        # Test resource method
        with pytest.raises(ValueError) as resource_exc_info:
            tailwind_plus_instance.get_component_as_resource(
                "Application UI.Forms.Input Groups.Label with leading icon",
                "html",
                "4",
                "none",
            )

        main_error = str(main_exc_info.value)
        resource_error = str(resource_exc_info.value)

        # Both should contain client-friendly format
        assert "mode='none'" in main_error
        assert "mode='none'" in resource_error

        # Both should contain similar structure (allowing for parameter naming differences)
        assert (
            "Component 'Application UI.Forms.Input Groups.Label with leading icon' cannot use mode='none'"
            in main_error
        )
        assert (
            "Component 'Application UI.Forms.Input Groups.Label with leading icon' cannot use mode='none'"
            in resource_error
        )

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
            (
                "get_component_as_resource",
                "Ecommerce.Product Lists.Simple",
                ("html", "4", "system"),
                "system",
            ),
            (
                "get_component_preview_as_resource",
                "Ecommerce.Product Lists.Simple",
                ("html", "4", "dark"),
                "dark",
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
