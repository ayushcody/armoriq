"""
MCP Registry — discovers tools from MCP servers at runtime.
Supports hot-reload without agent restart.
"""

import json, logging, os
from pathlib import Path
from mcp_client import StdioMCPClient, SSEMCPClient

logger = logging.getLogger(__name__)


class MCPRegistry:
    def __init__(self, config_path: str = "mcp_servers.json"):
        self.config_path = config_path
        self._clients: dict[str, StdioMCPClient | SSEMCPClient] = {}
        self._tool_map: dict[str, str] = {}   # tool_name -> server_name
        self._tools: list[dict] = []           # OpenAI format, ready for LLM

    async def start(self):
        await self._load_and_discover()

    async def reload(self):
        """Hot-reload without agent restart."""
        for client in self._clients.values():
            await client.stop()
        self._clients.clear()
        self._tool_map.clear()
        self._tools.clear()
        await self._load_and_discover()
        logger.info(f"Registry reloaded: {len(self._tools)} tools total")

    async def _load_and_discover(self):
        logger.info(f"Loading MCP config from: {self.config_path}")
        config = json.loads(Path(self.config_path).read_text())
        for srv in config["servers"]:
            try:
                logger.info(f"Connecting to MCP server: {srv['name']}...")
                client = self._build_client(srv)
                if hasattr(client, "start"):
                    await client.start()
                raw_tools = await client.list_tools()
                self._clients[srv["name"]] = client
                for tool in raw_tools:
                    self._tool_map[tool["name"]] = srv["name"]
                    self._tools.append(self._to_openai_tool(tool))
                logger.info(f"Successfully registered server [{srv['name']}] with {len(raw_tools)} tools")
            except Exception as e:
                logger.error(f"CRITICAL: Failed to connect to {srv['name']}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())

    def _build_client(self, srv: dict):
        if srv["type"] == "stdio":
            command = srv["command"]
            args = []
            for arg in srv.get("args", []):
                # If path is relative to config, make it absolute for Docker
                if arg.endswith(".py") and (arg.startswith("..") or arg.startswith(".")):
                    abs_path = os.path.abspath(os.path.join(os.path.dirname(self.config_path), arg))
                    args.append(abs_path)
                    logger.info(f"Resolved relative path for {srv['name']}: {arg} -> {abs_path}")
                else:
                    args.append(arg)
            return StdioMCPClient(srv["name"], command, args)
        elif srv["type"] == "sse":
            api_key = os.environ.get(srv["api_key_env"]) if srv.get("api_key_env") else None
            return SSEMCPClient(srv["name"], srv["url"], api_key)
        raise ValueError(f"Unknown transport type: {srv['type']}")

    def _to_openai_tool(self, mcp_tool: dict) -> dict:
        """Convert MCP tool definition to OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": mcp_tool["name"],
                "description": mcp_tool.get("description", ""),
                "parameters": mcp_tool.get("inputSchema", {"type": "object", "properties": {}})
            }
        }

    def get_all_tools(self) -> list[dict]:
        """Returns live tool list in OpenAI format. Called fresh every conversation."""
        return list(self._tools)

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        server_name = self._tool_map.get(tool_name)
        if not server_name:
            raise ValueError(f"No server registered for tool '{tool_name}'")
        return await self._clients[server_name].call_tool(tool_name, arguments)
