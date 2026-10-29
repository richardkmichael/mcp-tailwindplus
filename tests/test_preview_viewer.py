from mcp_tailwindplus.preview_viewer import get_preview_viewer_html


class TestPreviewViewerHTML:
    """Test the MCP Apps preview viewer HTML template."""

    def test_viewer_html_interpolates_server_version(self):
        """Test that the viewer HTML contains the actual server version."""
        html = get_preview_viewer_html()
        assert "{mcp_server_version}" not in html
        # Should contain a real version string in the App constructor
        assert 'version: "' in html

    def test_viewer_html_has_no_unresolved_placeholders(self):
        """Test that Python format placeholders are fully resolved."""
        html = get_preview_viewer_html()
        # All {{ }} should have been resolved to { } by .format()
        # No single { or } should remain outside of JS code blocks
        assert "{mcp_server_version}" not in html

    def test_viewer_html_contains_required_elements(self):
        """Test that the viewer HTML has the structural elements needed for rendering."""
        html = get_preview_viewer_html()
        assert "tw-component-css" in html
        assert "preview-container" in html
        assert "ontoolresult" in html
        assert "DOMParser" in html
        assert "tailwindcss" in html
