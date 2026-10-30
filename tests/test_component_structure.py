import time

from mcp_tailwindplus.component_structure import extract_structure


def test_classes_and_elements():
    assert extract_structure(
        '<div class="mt-2 flex"><span class="flex">Email</span><br></div>'
    ) == {
        "class:mt-2",
        "class:flex",
        "element:div.flex.mt-2",
        "element:span.flex",
        "element:br.",
    }


def test_order_and_nesting_are_ignored():
    original = '<div class="a b"><p class="c"></p><span class="d"></span></div>'
    edited = (
        '<div class="b a"><section><span class="d"></span></section>'
        '<p class="c"></p></div>'
    )
    assert extract_structure(edited) == extract_structure(original) | {
        "element:section."
    }


def test_code_and_icon_paths_are_skipped():
    """An `svg` element is a token, but its paths and the content of scripts
    and styles are not."""
    code = """
<svg class="size-5" viewBox="0 0 20 20"><path class="fill" d="M3 4a2" /></svg>
<script>const html = '<div class="in-script">'</script>
<style>.x { color: red }</style>
"""
    assert extract_structure(code) == {"class:size-5", "element:svg.size-5"}


def test_vue_class_bindings_and_templates():
    code = """<template>
  <li :class="[active ? 'bg-indigo-600 text-white' : 'text-gray-900', 'relative']" class="py-2" />
</template>"""
    assert extract_structure(code) == {
        "class:bg-indigo-600",
        "class:text-white",
        "class:text-gray-900",
        "class:relative",
        "class:py-2",
        "element:li.bg-indigo-600.py-2.relative.text-gray-900.text-white",
    }


def test_jsx_class_names():
    """`className` strings and the string literals of `className` expressions
    are classes; other expressions, such as an arrow function, are not."""
    code = """export default function Example() {
  return (
    <button
      onClick={() => setOpen(false)}
      className={classNames(open ? 'bg-gray-100' : '', `px-3 ${size}`)}
    >
      <span className="sr-only">Close</span>
    </button>
  )
}"""
    assert extract_structure(code, jsx=True) == {
        "class:bg-gray-100",
        "class:px-3",
        "class:sr-only",
        "element:button.bg-gray-100.px-3",
        "element:span.sr-only",
    }


def test_long_word_runs_take_linear_time():
    """A run of 40,000 word characters in JSX took seconds to read when
    matching attributes was quadratic in its length."""
    begun = time.perf_counter()
    extract_structure("<div>" + "a" * 40_000 + "</div>", jsx=True)
    assert time.perf_counter() - begun < 0.5


def test_unclosed_interpolation_takes_linear_time():
    """Unclosed `${` in a `className` template literal took seconds to read
    when matching interpolations was quadratic in their number."""
    code = "<div className={`" + "${ " * 40_000 + "`}></div>"
    begun = time.perf_counter()
    extract_structure(code, jsx=True)
    assert time.perf_counter() - begun < 0.5
