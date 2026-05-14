"""
FastAPI app — REST API + WebSocket endpoints for the Guarded Agent.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio, logging, os, sys
from dotenv import load_dotenv

from llm_client import LLMClient
from mcp_registry import MCPRegistry
from agent_loop import run_conversation
from log_store import LogStore

# policy_engine is a sibling package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from policy_engine.engine import PolicyEngine
from policy_engine.rule_store import RuleStore
from policy_engine.models import PolicyRule

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

llm: LLMClient
registry: MCPRegistry
policy: PolicyEngine
log_store: LogStore
ws_clients: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm, registry, policy, log_store
    log_store = LogStore()
    llm = LLMClient()
    registry = MCPRegistry(os.path.join(os.path.dirname(__file__), "..", "mcp_servers.json"))
    await registry.start()
    rule_store = RuleStore()
    policy = PolicyEngine(rule_store)

    async def _broadcast(entry: dict):
        dead = []
        for ws in ws_clients:
            try:
                await ws.send_json(entry)
            except Exception:
                dead.append(ws)
        for ws in dead:
            ws_clients.remove(ws)

    log_store.on_new_entry(_broadcast)
    yield


app = FastAPI(title="Guarded Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://armoriq.ayushchougula.in", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(body: dict):
    try:
        return await run_conversation(
            user_message=body["message"],
            conversation_id=body.get("conversation_id"),
            llm=llm, registry=registry, policy=policy, log_store=log_store,
        )
    except Exception as e:
        logging.error(f"Chat Route Error: {e}")
        return {"error": str(e), "status": "error"}


@app.post("/api/config/groq")
def configure_groq(body: dict):
    llm.set_api_key(body.get("api_key", ""))
    return {"status": "configured" if llm.is_configured() else "cleared"}


@app.get("/api/config/groq")
def get_groq_config():
    return {"is_configured": llm.is_configured()}


@app.get("/")
@app.get("/health")
def root_health():
    return {"status": "ok"}


@app.get("/api/health")
def health():
    tools = registry.get_all_tools()
    return {
        "status": "ok",
        "llm": llm.health_check(),
        "mcp_servers": len(registry._clients),
        "mcp_tools": len(tools),
        "mcp_tool_names": [{"name": t["function"]["name"], "description": t["function"].get("description", "")} for t in tools],
        "policy_rules": len(policy.list_rules()),
    }


@app.post("/api/mcp/reload")
async def mcp_reload():
    await registry.reload()
    return {"tools": len(registry.get_all_tools()), "status": "reloaded"}


@app.get("/api/rules")
def list_rules():
    return [r.to_dict() for r in policy.list_rules()]


@app.post("/api/rules")
def create_rule(body: dict):
    rule = PolicyRule(**body)
    return policy.create_rule(rule).to_dict()


@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: str, body: dict):
    body["id"] = rule_id
    rule = PolicyRule(**body)
    return policy.update_rule(rule).to_dict()


@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: str):
    policy.delete_rule(rule_id)
    return {"deleted": rule_id}


@app.patch("/api/rules/{rule_id}/toggle")
def toggle_rule(rule_id: str, body: dict):
    rule = policy.toggle_rule(rule_id, body["enabled"])
    return rule.to_dict() if rule else {"error": "not found"}


@app.get("/api/logs")
async def get_logs(limit: int = 50, offset: int = 0, tool_name: str = None, action: str = None):
    return await log_store.query(limit=limit, offset=offset, tool_name=tool_name, action=action)


@app.get("/api/approvals")
def list_approvals():
    return policy.get_pending_approvals()


@app.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: str):
    policy.resolve_approval(approval_id, "approved")
    return {"status": "approved"}


@app.post("/api/approvals/{approval_id}/deny")
def deny(approval_id: str):
    policy.resolve_approval(approval_id, "denied")
    return {"status": "denied"}


@app.get("/api/stats")
async def get_stats():
    return await log_store.get_stats()


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
