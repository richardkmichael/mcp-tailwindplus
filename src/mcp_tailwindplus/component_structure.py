"""Structural tokens of TailwindPlus component code, for finding the component
code was copied from."""

import re
from html.parser import HTMLParser

# Elements whose content is code, not markup.
_SKIPPED_ELEMENTS = frozenset({"script", "style"})

# Vue's `<template>` groups markup without rendering an element of its own.
_TRANSPARENT_ELEMENTS = frozenset({"template"})

# Attributes whose quoted strings are classes: Vue's class bindings, such as
# `:class="[active ? 'bg-indigo-600' : 'bg-white', 'rounded-md']"`.
_CLASS_BINDINGS = frozenset({":class", "v-bind:class"})

_QUOTED = re.compile(r"""'([^']*)'|"([^"]*)"|`([^`]*)`""")
# An unclosed interpolation runs to the end of its string. Requiring the closing
# brace made each unclosed `${` rescan the rest of the string.
_INTERPOLATION = re.compile(r"\$\{[^}]*\}?")
# The lookbehind starts a match only at the start of an attribute name; without
# it, a long run of word characters is rescanned from each of its positions.
_JSX_EXPRESSION_ATTRIBUTE = re.compile(r"(?<![\w:-])([\w:-]+)=\{")
_BRACE = re.compile(r"[{}]")


def _quoted_words(expression: str) -> list[str]:
    """Return the words of the string literals in a JavaScript expression."""
    words = []
    for match in _QUOTED.finditer(expression):
        text = next(group for group in match.groups() if group is not None)
        words.extend(_INTERPOLATION.sub(" ", text).split())
    return words


def _jsx_as_html(jsx: str) -> str:
    """Rewrite JSX attributes so HTMLParser reads their classes and tag ends.

    `className={...}` becomes a `class` attribute holding the string literals of
    the expression. Other `{...}` attribute values become empty strings, so an
    arrow function's `=>` does not end its tag.
    """
    pieces = []
    position = 0
    for match in _JSX_EXPRESSION_ATTRIBUTE.finditer(jsx):
        if match.start() < position:
            continue
        depth, end = 1, len(jsx)
        for brace in _BRACE.finditer(jsx, match.end()):
            depth += 1 if brace.group() == "{" else -1
            if not depth:
                end = brace.end()
                break
        name = match.group(1)
        expression = jsx[match.end() : end - 1]
        value = " ".join(_quoted_words(expression)) if name == "className" else ""
        pieces.append(f'{jsx[position : match.start()]}{name}="{value}"')
        position = end
    pieces.append(jsx[position:])
    return "".join(pieces).replace('className="', 'class="')


class _StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: set[str] = set()
        self._skipped_depth = 0
        self._svg_depth = 0

    def _element(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if (
            self._skipped_depth
            or self._svg_depth
            or tag in _SKIPPED_ELEMENTS
            or tag in _TRANSPARENT_ELEMENTS
        ):
            return
        classes = set()
        for key, value in attrs:
            if key == "class" and value:
                classes.update(value.split())
            elif key in _CLASS_BINDINGS and value:
                classes.update(_quoted_words(value))
        self.tokens.update(f"class:{name}" for name in classes)
        self.tokens.add(f"element:{tag}.{'.'.join(sorted(classes))}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._element(tag, attrs)
        if tag in _SKIPPED_ELEMENTS:
            self._skipped_depth += 1
        # An icon's paths draw its shape; the `svg` element itself is a token.
        elif tag == "svg":
            self._svg_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._element(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIPPED_ELEMENTS and self._skipped_depth:
            self._skipped_depth -= 1
        elif tag == "svg" and self._svg_depth:
            self._svg_depth -= 1


def extract_structure(code: str, jsx: bool = False) -> frozenset[str]:
    """Return the structural tokens of HTML, Vue template or JSX code.

    The tokens are each class, as `class:rounded-md`, and each element as its
    tag and sorted classes, as `element:button.px-3.rounded-md`. Order and nesting
    are left out, so code whose elements or classes were reordered, or wrapped in
    new elements, keeps its tokens.
    """
    parser = _StructureParser()
    parser.feed(_jsx_as_html(code) if jsx else code)
    parser.close()
    return frozenset(parser.tokens)
