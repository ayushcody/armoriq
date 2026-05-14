"""
MCP Client — supports both stdio and SSE transports.
"""

import asyncio, json, uuid, logging, httpx
from pathlib import Path

logger = logging.getLogger(__name__)


class StdioMCPClient:
    """MCP client over stdio transport (JSON-RPC 2.0, newline-delimited)."""

    def __init__(self, name: str, command: str, args: list[str]):
        self.name = name
        self.command = command
        self.args = args
        self._process: asyncio.subprocess.Process | None = None
        self._pending: dict[str, asyncio.Future] = {}

    async def start(self):
        import os
        self._process = await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy()
        )
        asyncio.create_task(self._read_loop())
        await self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "guarded-agent", "version": "1.0.0"}
        })
        logger.info(f"[{self.name}] MCP stdio server started (pid={self._process.pid})")

    async def _read_loop(self):
        assert self._process and self._process.stdout
        while not self._process.stdout.at_eof():
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break
                msg = json.loads(line.decode().strip())
                msg_id = str(msg.get("id"))
                if msg_id in self._pending:
                    fut = self._pending.pop(msg_id)
                    if not fut.done():
                        if "error" in msg:
                            fut.set_exception(RuntimeError(msg["error"]["message"]))
                        else:
                            fut.set_result(msg.get("result"))
            except Exception as e:
                logger.error(f"[{self.name}] Read loop error: {e}")

    async def _send(self, method: str, params: dict, timeout: float = 10.0) -> dict:
        msg_id = str(uuid.uuid4())
        payload = json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
        loop = asyncio.get_event_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[msg_id] = fut
        assert self._process and self._process.stdin
        self._process.stdin.write((payload + "\n").encode())
        await self._process.stdin.drain()
        return await asyncio.wait_for(fut, timeout=timeout)

    async def list_tools(self) -> list[dict]:
        result = await self._send("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> dict:
        return await self._send("tools/call", {"name": name, "arguments": arguments})

    async def stop(self):
        if self._process:
            self._process.terminate()
            await self._process.wait()


class SSEMCPClient:
    """MCP client over SSE/HTTP transport (for remote MCP servers like Exa)."""

    def __init__(self, name: str, url: str, api_key: str | None = None):
        self.name = name
        self.url = url
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["x-api-key"] = api_key

    async def list_tools(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.url, headers=self._headers, json={
                "jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}
            })
            resp.raise_for_status()
            return resp.json().get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: dict) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.url, headers=self._headers, json={
                "jsonrpc": "2.0", "id": "1", "method": "tools/call",
                "params": {"name": name, "arguments": arguments}
            })
            resp.raise_for_status()
            result = resp.json()
            if "error" in result:
                raise RuntimeError(result["error"]["message"])
            return result["result"]

    async def stop(self):
        pass  # SSE clients are stateless
