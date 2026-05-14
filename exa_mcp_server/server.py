import sys, json, logging, os
from exa_py import Exa

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format="%(asctime)s [WEB-SEARCH] %(levelname)s %(message)s")
logger = logging.getLogger("web-search")

exa_key = os.environ.get("EXA_API_KEY")
exa = Exa(exa_key) if exa_key else None

TOOLS = [
    {
        "name": "search_web",
        "description": "Search the live web. Returns URLs with titles and highlights. Use for general research.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "num_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_web_answer",
        "description": "Get a direct, cited answer to a question using live web data. Best for factual lookups.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The question to answer."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_page_contents",
        "description": "Fetch full text of specific URLs for deep analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "urls": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["urls"]
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
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "web-search", "version": "1.1.0"}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                name = msg["params"]["name"]
                args = msg["params"].get("arguments", {})
                text = ""

                if not exa:
                    text = "Error: EXA_API_KEY missing. Please set it in Render environment variables."
                else:
                    try:
                        if name == "search_web":
                            res = exa.search(args["query"], num_results=args.get("num_results", 5), type="auto", contents={"highlights": True})
                            if not res.results:
                                text = f"No results found for '{args['query']}'."
                            else:
                                text = f"Results for '{args['query']}':\n\n"
                                for r in res.results:
                                    h = r.highlights[0] if getattr(r, 'highlights', None) else "No snippet."
                                    text += f"### {r.title}\nURL: {r.url}\nSnippet: {h}\n\n"

                        elif name == "get_web_answer":
                            res = exa.answer(args["query"])
                            text = f"Answer: {res.answer}\n\nSources:\n"
                            for c in getattr(res, 'citations', []):
                                text += f"- {getattr(c, 'title', 'Source')} ({getattr(c, 'url', 'N/A')})\n"

                        elif name == "get_page_contents":
                            res = exa.get_contents(args["urls"], text=True)
                            text = "Contents:\n\n"
                            for r in res.results:
                                content = r.text[:1500] + "..." if len(r.text) > 1500 else r.text
                                text += f"--- {r.url} ---\n{content}\n\n"
                    except ValueError as ve:
                        text = f"API Error: {str(ve)}"
                    except Exception as e:
                        text = f"Unexpected Error: {str(e)}"

                result = {"content": [{"type": "text", "text": text}]}

            if result is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)
        except Exception as e:
            logger.error(f"Fatal Server Error: {e}")
            if msg_id:
                print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}), flush=True)

if __name__ == "__main__":
    main()
