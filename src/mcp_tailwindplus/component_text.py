"""Searchable text extracted from TailwindPlus component code."""

import re
from html.parser import HTMLParser

# Attributes whose values are visible text or name a field's purpose.
_PROSE_ATTRIBUTES = frozenset(
    {"placeholder", "aria-label", "alt", "title", "type", "name", "autocomplete"}
)

# `type` values that say nothing about a component's purpose, unlike `email` or
# `password`.
_GENERIC_TYPES = frozenset({"button", "submit", "reset", "text", "hidden"})

# Elements whose content is code or graphics, not prose.
_NON_PROSE_ELEMENTS = frozenset({"script", "style", "svg"})

# Elements whose tag name says what a part of a component is. Elements found in
# nearly every component, such as `button`, `input` or `img`, are left out.
_SEMANTIC_ELEMENTS = frozenset(
    {
        "address",
        "aside",
        "blockquote",
        "details",
        "dialog",
        "fieldset",
        "footer",
        "form",
        "header",
        "nav",
        "progress",
        "select",
        "table",
        "textarea",
    }
)

# Comments that label a part of a component, such as "Mobile menu", are short.
# Longer comments are implementation notes.
_MAX_LABEL_WORDS = 6

# Comments containing these hold code, such as class lists for states
# (`Active: "text-yellow-400"`) or template instructions, not labels.
_CODE_CHARACTERS = frozenset('"`<>{}=')

# Packages whose imports name icons and UI components, such as `EnvelopeIcon` or
# `Dialog`. React's own imports are hooks, not component vocabulary.
_PART_PACKAGES = ("@headlessui/", "@heroicons/")

_IMPORT = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]")
_CAMEL_CASE_WORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


class _ComponentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.prose: list[str] = []
        self.parts: list[str] = []
        self._non_prose_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _NON_PROSE_ELEMENTS:
            self._non_prose_depth += 1
        if tag.startswith("el-"):
            self.parts.append(tag.removeprefix("el-").replace("-", " "))
        elif tag in _SEMANTIC_ELEMENTS:
            self.parts.append(tag)
        self.prose.extend(
            value
            for key, value in attrs
            if key in _PROSE_ATTRIBUTES
            and value
            and not (key == "type" and value in _GENERIC_TYPES)
        )

    def handle_endtag(self, tag: str) -> None:
        if tag in _NON_PROSE_ELEMENTS and self._non_prose_depth:
            self._non_prose_depth -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text and not self._non_prose_depth:
            self.prose.append(text)

    def handle_comment(self, data: str) -> None:
        text = " ".join(data.split())
        if len(text.split()) <= _MAX_LABEL_WORDS and not _CODE_CHARACTERS & set(text):
            self.parts.append(text)


def _parse(html: str) -> _ComponentParser:
    parser = _ComponentParser()
    parser.feed(html)
    return parser


def _unique(fragments: list[str]) -> list[str]:
    """Drop repeated fragments, case-insensitively, keeping the first of each,
    and fragments with no letters or digits, such as a lone '.'."""
    seen = set()
    unique = []
    for fragment in fragments:
        if not any(char.isalnum() for char in fragment):
            continue
        if fragment.lower() not in seen:
            seen.add(fragment.lower())
            unique.append(fragment)
    return unique


def extract_prose(html: str) -> list[str]:
    """Return the visible text and descriptive attribute values of HTML code.

    Fragments are in document order, without repeats, so a field whose label,
    `name` and `type` are all "email" yields "Email" once.
    """
    return _unique(_parse(html).prose)


def extract_parts(html: str, react: str) -> list[str]:
    """Return the names of a component's parts.

    Parts are named by:

    - Heroicons and Headless UI imports in the React code, as words, such as
      `EnvelopeIcon` as "envelope icon"
    - TailwindPlus Elements tags in the HTML code, such as `<el-dialog-panel>` as
      "dialog panel"
    - semantic HTML elements, such as `nav` or `table`
    - short comments labeling a part, such as "Mobile menu"
    """
    return _parts(_parse(html), react)


def extract_parts_and_prose(html: str, react: str) -> tuple[list[str], list[str]]:
    """Return a component's parts and prose, as extract_parts and
    extract_prose do, parsing the HTML code once."""
    parser = _parse(html)
    return _parts(parser, react), _unique(parser.prose)


def _parts(parser: _ComponentParser, react: str) -> list[str]:
    imported = [
        # `ChevronDownIcon as ChevronIcon` imports ChevronDownIcon.
        name.split(" as ")[0].strip()
        for names, package in _IMPORT.findall(react)
        if package.startswith(_PART_PACKAGES)
        for name in names.split(",")
        if name.strip()
    ]
    words = [" ".join(_CAMEL_CASE_WORD.findall(name)).lower() for name in imported]
    return _unique(words + parser.parts)
