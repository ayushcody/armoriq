import sys, json, logging

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format="%(asctime)s [RESEARCH] %(levelname)s %(message)s")
logger = logging.getLogger("research-assistant")

TOOLS = [
    {
        "name": "search_documentation",
        "description": "Search internal architecture documentation and SOPs for patterns.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    }
]

def main():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line: continue
        try:
            msg = json.loads(line)
            method = msg.get("method", "")
            msg_id = msg.get("id")
            result = None

            if method == "initialize":
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "research-assistant", "version": "1.0.0"}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                name = msg["params"]["name"]
                args = msg["params"].get("arguments", {})
                if name == "search_documentation":
                    text = f"Internal Doc Search for '{args.get('query')}': Found architectural references in /docs/topology and /docs/security-policy."
                result = {"content": [{"type": "text", "text": text}]}

            if result is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)
        except Exception as e:
            logger.error(f"Error: {e}")
            if msg_id:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)}
                }), flush=True)

if __name__ == "__main__":
    main()
