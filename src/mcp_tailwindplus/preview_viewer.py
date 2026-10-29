from functools import cache
from importlib.metadata import version as mcp_server_version

# MCP Apps viewer template derived from the common TailwindPlus preview shell.
# The ontoolresult callback receives full preview HTML, extracts the <style>
# and <body> content, and injects them into this template's DOM.
_PREVIEW_VIEWER_HTML = """\
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<link rel="preconnect" href="https://rsms.me/">
<link rel="stylesheet" href="https://rsms.me/inter/inter.css">
<script src="https://cdn.jsdelivr.net/npm/@tailwindplus/elements@insiders" type="module"></script>
<style id="tw-component-css"></style>
<style>body {{ -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }}</style>
<body>
<div id="preview-container"></div>
<script type="module">
  import {{ App }} from "https://unpkg.com/@modelcontextprotocol/ext-apps@1.2.2/app-with-deps";

  const app = new App({{ name: "TailwindPlus Preview", version: "{mcp_server_version}" }});

  // Keep placeholder links and forms in the preview from navigating the frame.
  document.addEventListener("click", (event) => {{
    if (event.target.closest('a[href="#"]')) event.preventDefault();
  }}, {{ capture: true }});
  document.addEventListener("submit", (event) => event.preventDefault());

  app.ontoolresult = ({{ content }}) => {{
    const text = content?.find(c => c.type === "text");
    if (!text) return;

    const parser = new DOMParser();
    const doc = parser.parseFromString(text.text, "text/html");

    // Extract compiled component CSS from the preview HTML
    const styles = doc.querySelectorAll("style");
    let componentCSS = "";
    for (const style of styles) {{
      if (style.textContent.includes("tailwindcss")) {{
        componentCSS = style.textContent;
        break;
      }}
    }}
    document.getElementById("tw-component-css").textContent = componentCSS;

    // Extract component markup from the preview body
    document.getElementById("preview-container").innerHTML = doc.body.innerHTML;
  }};

  await app.connect();
</script>
</body>
"""


@cache
def get_preview_viewer_html() -> str:
    """Return the MCP Apps viewer HTML for rendering TailwindPlus component previews."""
    return _PREVIEW_VIEWER_HTML.format(
        mcp_server_version=mcp_server_version("mcp-tailwindplus")
    )
