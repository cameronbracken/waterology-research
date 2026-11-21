import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

// Register the Waterology stdio server with Pi's built-in MCP support.
// A server named "waterology" in mcp.json takes precedence over this one.
export default function (pi: ExtensionAPI) {
  pi.registerMcpServer("waterology", {
    command: "waterology-mcp",
    description:
      "Waterology reference and dataset tools: scholarly search, Zotero sync, and Hugging Face Hub inspection",
  });
}
