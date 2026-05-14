import sys, json, logging, os
from exa_py import Exa

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format="%(asctime)s [WEB-SEARCH] %(levelname)s %(message)s")
logger = logging.getLogger("web-search")

exa_key = os.environ.get("EXA_API_KEY")
exa = Exa(exa_key) if exa_key else None

TOOLS = [
    {
        "name": "search_web",
        "description": "Search the live web using Exa for real-time information.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "num_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
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
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "web-search", "version": "1.0.0"}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                name = msg["params"]["name"]
                args = msg["params"].get("arguments", {})
                if name == "search_web":
                    if not exa:
                        text = "Error: EXA_API_KEY not configured."
                    else:
                        res = exa.search(args["query"], num_results=args.get("num_results", 5), use_autoprompt=True)
                        text = f"Exa Search for '{args['query']}':\n" + "\n".join([f"- {r.title} ({r.url})" for r in res.results])
                result = {"content": [{"type": "text", "text": text}]}

            if result is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
