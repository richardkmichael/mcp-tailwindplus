import os
import json

from fastmcp import FastMCP

@dataclass
class TailwindUI

    def init(self):
        tailwindui_data_file = os.env("MCP_TAILWINDPLUS_DATA") || "tmp/tailwindplus-components-2025-06-10-221317.json"

        with os.read(tailwindui_data) as f:
            self.tailwindui_data = json.load(f)


@tailwind_data = TailwindUI()

mcp = FastMCP("tailwindui")

@mcp.tool
async def list_all_components():
    # jq -r 'paths(scalars) as $p | $p | map("\"" + . + "\"") | join(".")'

    await asyncio.subprocess("jq")


# if __name__ == "__main__":

