import sys, json, logging, os
from exa_py import Exa

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format="%(asctime)s [WEB-SEARCH] %(levelname)s %(message)s")
logger = logging.getLogger("web-search")

exa_key = os.environ.get("EXA_API_KEY")
exa = Exa(exa_key) if exa_key else None

TOOLS = [
    {
        "name": "search_web",
        "description": "Search the live web using Exa. Returns a list of relevant URLs with titles and highlights.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query (natural language works best)."},
                "num_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_web_answer",
        "description": "Get a direct answer to a question based on a live web search. Best for factual questions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The question to answer (e.g., 'What is the latest valuation of SpaceX?')"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_page_contents",
        "description": "Fetch the full text content of specific URLs for deep analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of URLs to crawl."
                }
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
                result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "web-search", "version": "1.0.0"}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                name = msg["params"]["name"]
                args = msg["params"].get("arguments", {})
                text = ""

                if not exa:
                    text = "Error: EXA_API_KEY not configured on server. Please set it in Render environment variables."
                else:
                    if name == "search_web":
                        res = exa.search(args["query"], num_results=args.get("num_results", 5), use_autoprompt=True, contents={"highlights": True})
                        if not res.results:
                            text = f"Exa Search: No results found for '{args['query']}'."
                        else:
                            text = f"Top results for '{args['query']}':\n\n"
                            for r in res.results:
                                highlight = r.highlights[0] if r.highlights else "No snippet available."
                                text += f"### {r.title}\nURL: {r.url}\nSnippet: {highlight}\n\n"

                    elif name == "get_web_answer":
                        res = exa.answer(args["query"])
                        text = f"Answer: {res.answer}\n\nSources used:\n"
                        for c in res.citations:
                            text += f"- {c.title} ({c.url})\n"

                    elif name == "get_page_contents":
                        res = exa.get_contents(args["urls"], text=True)
                        text = "Extracted contents:\n\n"
                        for r in res.results:
                            content = r.text[:2000] + "..." if len(r.text) > 2000 else r.text
                            text += f"--- CONTENT FROM {r.url} ---\n{content}\n\n"

                result = {"content": [{"type": "text", "text": text}]}

            if result is not None:
                print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if msg_id:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32603, "message": str(e)}
                }), flush=True)

if __name__ == "__main__":
    main()
