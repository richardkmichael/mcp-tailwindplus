from mcp_tailwindplus.component_text import extract_parts, extract_prose

FIELD_HTML = """
<div>
  <label for="email" class="block text-sm">Email</label>
  <input id="email" type="email" name="email" placeholder="you@example.com"
         autocomplete="email" class="block w-full" />
</div>
"""

DIALOG_HTML = """
<button command="show-modal">Open dialog</button>
<el-dialog>
  <dialog aria-labelledby="dialog-title">
    <el-dialog-panel>
      <svg viewBox="0 0 24 24"><title>Check</title><path d="M4.5 12.75" /></svg>
      <h3 id="dialog-title">Payment successful</h3>
      <script>console.log("not prose")</script>
      <style>.hidden { display: none }</style>
    </el-dialog-panel>
  </dialog>
</el-dialog>
"""

DIALOG_REACT = """
import { useState } from 'react'
import { Dialog, DialogPanel, DialogTitle } from '@headlessui/react'
import { CheckIcon, ChevronDownIcon as ChevronIcon } from '@heroicons/react/24/outline'
"""


class TestExtractProse:
    def test_text_and_descriptive_attributes(self):
        assert extract_prose(FIELD_HTML) == ["Email", "you@example.com"]

    def test_skips_classes_ids_and_other_attributes(self):
        prose = " ".join(extract_prose(FIELD_HTML))
        assert "block" not in prose
        assert "w-full" not in prose

    def test_skips_script_style_and_svg_content(self):
        assert extract_prose(DIALOG_HTML) == ["Open dialog", "Payment successful"]

    def test_collapses_whitespace(self):
        assert extract_prose("<p>Sign\n   in   now</p>") == ["Sign in now"]

    def test_skips_generic_types_and_punctuation(self):
        html = """
        <form>
          <input type="password" name="current-password" />
          <button type="submit">Save</button>
          <p>Read our <a href="#">privacy policy</a>.</p>
        </form>
        """
        assert extract_prose(html) == [
            "password",
            "current-password",
            "Save",
            "Read our",
            "privacy policy",
        ]


class TestExtractParts:
    def test_icon_and_ui_component_imports_as_words(self):
        assert extract_parts("", DIALOG_REACT) == [
            "dialog",
            "dialog panel",
            "dialog title",
            "check icon",
            "chevron down icon",
        ]

    def test_skips_react_imports(self):
        assert "use state" not in extract_parts("", DIALOG_REACT)

    def test_elements_tags_as_words(self):
        assert extract_parts(DIALOG_HTML, "") == ["dialog", "dialog panel"]

    def test_semantic_elements(self):
        html = """
        <header><nav><a href="#">Home</a></nav></header>
        <form><button>Go</button><table></table></form>
        """
        assert extract_parts(html, "") == ["header", "nav", "form", "table"]

    def test_comment_labels(self):
        html = """
        <!-- Mobile menu -->
        <!-- Profile dropdown -->
        <!-- Active: "text-yellow-400", Default: "text-gray-300" -->
        <!-- This example requires updating your template: `<html class="h-full">` -->
        <!-- Presentational element used to render the bottom shadow, if we put it on the panel -->
        """
        assert extract_parts(html, "") == ["Mobile menu", "Profile dropdown"]

    def test_combined_without_repeats(self):
        parts = extract_parts(DIALOG_HTML, DIALOG_REACT)
        assert parts.count("dialog") == 1
        assert parts.count("dialog panel") == 1
