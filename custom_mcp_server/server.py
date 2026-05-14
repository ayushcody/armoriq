"""
DevOps Sentinel MCP Server — stdio transport.
Exposes 5 infrastructure monitoring tools via JSON-RPC 2.0 over stdin/stdout.
All logging goes to stderr to keep the protocol channel clean.
"""

import sys, json, uuid, logging
from datetime import datetime
from jsonschema import validate, ValidationError
from mock_data import SERVICES, LOGS, ALERTS

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                    format="%(asctime)s [MCP] %(levelname)s %(message)s")
logger = logging.getLogger("devops-sentinel")

TOOLS = [
    {
        "name": "list_services",
        "description": "List all registered microservices and their current status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter_status": {"type": "string", "enum": ["healthy", "degraded", "down", "all"]}
            },
            "additionalProperties": False,
        }
    },
    {
        "name": "get_service_logs",
        "description": "Fetch recent logs for a specific service",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "lines": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
            },
            "required": ["service_name"],
            "additionalProperties": False,
        }
    },
    {
        "name": "trigger_alert",
        "description": "Trigger a monitoring alert for a service",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "critical"]},
                "message": {"type": "string", "maxLength": 200}
            },
            "required": ["service_name", "severity", "message"],
            "additionalProperties": False,
        }
    },
    {
        "name": "scale_service",
        "description": "Scale a service instance count up or down",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "replicas": {"type": "integer", "minimum": 1, "maximum": 10}
            },
            "required": ["service_name", "replicas"],
            "additionalProperties": False,
        }
    },
    {
        "name": "run_healthcheck",
        "description": "Run a health check on a service and return detailed diagnostics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "deep": {"type": "boolean", "default": False}
            },
            "required": ["service_name"],
            "additionalProperties": False,
        }
    },
]

TOOL_SCHEMAS = {t["name"]: t["inputSchema"] for t in TOOLS}


def mcp_error(code: int, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def handle_list_services(args: dict) -> dict:
    result = []
    for name, info in SERVICES.items():
        if args.get("filter_status") and args["filter_status"] != "all" and info["status"] != args["filter_status"]:
            continue
        result.append({"name": name, **info})
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


def handle_get_service_logs(args: dict) -> dict:
    name = args["service_name"]
    if name not in SERVICES:
        return mcp_error(-32602, f"Unknown service: {name}")
    lines = args.get("lines", 20)
    logs = LOGS.get(name, [])[-lines:]
    return {"content": [{"type": "text", "text": json.dumps({"service": name, "log_lines": logs})}]}


def handle_trigger_alert(args: dict) -> dict:
    alert = {"alert_id": str(uuid.uuid4()), "status": "queued",
             "service": args["service_name"], "severity": args["severity"],
             "message": args["message"], "timestamp": datetime.utcnow().isoformat()}
    ALERTS.append(alert)
    return {"content": [{"type": "text", "text": json.dumps(alert)}]}


def handle_scale_service(args: dict) -> dict:
    name = args["service_name"]
    if name not in SERVICES:
        return mcp_error(-32602, f"Unknown service: {name}")
    old = SERVICES[name]["replicas"]
    SERVICES[name]["replicas"] = args["replicas"]
    return {"content": [{"type": "text", "text": json.dumps({
        "service": name, "old_replicas": old,
        "new_replicas": args["replicas"], "status": "applied"
    })}]}


def handle_run_healthcheck(args: dict) -> dict:
    name = args["service_name"]
    if name not in SERVICES:
        return mcp_error(-32602, f"Unknown service: {name}")
    svc = SERVICES[name]
    healthy = svc["status"] == "healthy"
    return {"content": [{"type": "text", "text": json.dumps({
        "service": name, "healthy": healthy,
        "checks": {"connectivity": healthy, "db": svc["status"] != "down", "cache": healthy},
        "latency_ms": 12 if healthy else 9999,
        "deep_scan": args.get("deep", False)
    })}]}


HANDLERS = {
    "list_services": handle_list_services,
    "get_service_logs": handle_get_service_logs,
    "trigger_alert": handle_trigger_alert,
    "scale_service": handle_scale_service,
    "run_healthcheck": handle_run_healthcheck,
}


def dispatch(name: str, arguments: dict) -> dict:
    if name not in HANDLERS:
        return mcp_error(-32601, f"Unknown tool: {name}")
    try:
        validate(instance=arguments, schema=TOOL_SCHEMAS[name])
    except ValidationError as e:
        return mcp_error(-32602, f"Invalid arguments: {e.message}")
    try:
        return HANDLERS[name](arguments)
    except Exception as e:
        return mcp_error(-32603, f"Tool execution error: {str(e)}")


def main():
    logger.info("DevOps Sentinel MCP server starting on stdio")
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            logger.debug(f"<-- {msg}")
            method = msg.get("method", "")
            msg_id = msg.get("id")

            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "devops-sentinel", "version": "1.0.0"}
                }
            elif method == "notifications/initialized":
                continue  # fire-and-forget, no response
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                params = msg.get("params", {})
                result = dispatch(params.get("name", ""), params.get("arguments", {}))
                if "error" in result:
                    response = {"jsonrpc": "2.0", "id": msg_id, "error": result["error"]}
                    logger.debug(f"--> {response}")
                    print(json.dumps(response), flush=True)
                    continue
            else:
                response = {"jsonrpc": "2.0", "id": msg_id,
                           "error": {"code": -32601, "message": f"Unknown method: {method}"}}
                print(json.dumps(response), flush=True)
                continue

            response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
            logger.debug(f"--> {response}")
            print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON input: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
