import sys, json, logging

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format="%(asctime)s [RESEARCH] %(levelname)s %(message)s")
logger = logging.getLogger("research-assistant")

TOOLS = [
    {
        "name": "search_documentation",
        "description": "Search internal documentation for architecture patterns or SOPs.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "get_system_metrics",
        "description": "Retrieve historical performance metrics for a specific system component.",
        "inputSchema": {"type": "object", "properties": {"component": {"type": "string"}}, "required": ["component"]}
    },
    {
        "name": "summarize_incidents",
        "description": "Summarize all infrastructure incidents from the last N days.",
        "inputSchema": {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}}
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
                    text = f"Search result for '{args.get('query')}': Found 3 relevant architecture diagrams in /docs/arch."
                elif name == "get_system_metrics":
                    text = f"Metrics for {args.get('component')}: Avg Latency: 45ms, Throughput: 1.2k req/sec, Error Rate: 0.01%"
                elif name == "summarize_incidents":
                    text = f"Incident Summary (Last {args.get('days', 7)} days): 2 minor network blips, 1 database failover (resolved)."
                result = {"content": [{"type": "text", "text": text}]}

            if result is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
