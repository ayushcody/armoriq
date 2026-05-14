from mcp.server.fastmcp import FastMCP
from exa_py import Exa
import os

# Initialize FastMCP server
mcp = FastMCP("Web-Search")

# Initialize Exa client
exa_key = os.environ.get("EXA_API_KEY")
exa = Exa(exa_key) if exa_key else None

@mcp.tool()
async def search_web(query: str, num_results: int = 5) -> str:
    \"\"\"Search the live web using Exa for real-time information.\"\"\"
    if not exa:
        return "Error: EXA_API_KEY not configured on server."
    
    try:
        results = exa.search(query, num_results=num_results, use_autoprompt=True)
        summary = f"Exa Search results for '{query}':\n\n"
        for r in results.results:
            summary += f"- {r.title} ({r.url})\n"
        return summary
    except Exception as e:
        return f"Exa Search failed: {str(e)}"

if __name__ == "__main__":
    mcp.run()
