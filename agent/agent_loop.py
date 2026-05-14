"""
Agent loop — core tool-use conversation loop with policy intercept.
"""

import json, asyncio, logging, uuid
from datetime import datetime

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a DevOps assistant with access to infrastructure monitoring tools.
Use your tools to answer questions about service health, logs, and operations.
When a tool is blocked by policy, explain this to the user clearly without attempting to bypass it.
Never suggest workarounds to policy restrictions. Never try to call tools in unusual ways."""


async def run_conversation(
    user_message: str,
    llm,           # LLMClient
    registry,      # MCPRegistry
    policy,        # PolicyEngine
    log_store,     # LogStore
    conversation_id: str | None = None,
) -> dict:
    conversation_id = conversation_id or str(uuid.uuid4())
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]
    tools = registry.get_all_tools()   # fresh every conversation — never cached
    total_tokens = {"prompt": 0, "completion": 0}
    tool_calls_log = []

    while True:
        response = llm.chat(messages=messages, tools=tools if tools else None)

        # Track tokens
        usage = response.usage
        if usage:
            total_tokens["prompt"]     += usage.prompt_tokens or 0
            total_tokens["completion"] += usage.completion_tokens or 0

        choice = response.choices[0]
        msg = choice.message

        # Final answer — no more tool calls
        if choice.finish_reason == "stop" or not msg.tool_calls:
            await log_store.save_conversation(conversation_id, tool_calls_log, total_tokens)
            return {
                "reply": msg.content,
                "conversation_id": conversation_id,
                "tool_calls": tool_calls_log,
                "tokens": total_tokens,
                "backend": llm.active_backend,
            }

        # LLM requested tool calls — process each
        messages.append(msg.model_dump(exclude_none=True))

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            call_id = tool_call.id

            # *** POLICY INTERCEPT — happens before every single tool execution ***
            decision = policy.evaluate({"name": fn_name, "args": fn_args})

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "conversation_id": conversation_id,
                "tool_name": fn_name,
                "server_name": registry._tool_map.get(fn_name, "unknown"),
                "arguments": fn_args,
                "policy_decision": decision["action"],
                "rule_id": decision.get("rule_id"),
                "reason": decision.get("reason"),
            }

            if decision["action"] == "BLOCK":
                logger.info(f"BLOCKED tool={fn_name} reason={decision['reason']}")
                tool_result = f"[POLICY BLOCK] Tool '{fn_name}' was blocked. Reason: {decision['reason']}"

            elif decision["action"] == "REQUIRE_APPROVAL":
                approval_id = decision["approval_id"]
                timeout = decision["timeout"]
                logger.info(f"AWAITING APPROVAL tool={fn_name} approval_id={approval_id}")
                # Notify log store immediately (dashboard needs to show it)
                log_entry["approval_id"] = approval_id
                await log_store.append_tool_call(log_entry)
                approved = await _wait_for_approval(approval_id, policy, timeout)
                if approved:
                    tool_result = await _execute_tool(registry, fn_name, fn_args)
                    log_entry["policy_decision"] = "APPROVED"
                else:
                    tool_result = f"[APPROVAL DENIED/TIMEOUT] Tool '{fn_name}' was not approved in time."
                    log_entry["policy_decision"] = "DENIED"

            else:  # ALLOW
                tool_result = await _execute_tool(registry, fn_name, fn_args)
                log_entry["result_preview"] = str(tool_result)[:200]

            tool_calls_log.append(log_entry)
            await log_store.append_tool_call(log_entry)

            # Feed result back to LLM — regardless of block/allow/deny
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": tool_result if isinstance(tool_result, str) else json.dumps(tool_result),
            })


async def _execute_tool(registry, name: str, args: dict) -> dict | str:
    try:
        return await registry.call_tool(name, args)
    except Exception as e:
        logger.error(f"Tool execution error [{name}]: {e}")
        return {"error": str(e), "tool": name}


async def _wait_for_approval(approval_id: str, policy, timeout: int) -> bool:
    """Poll every 2s for approval decision. Returns True=approved, False=denied/timeout."""
    elapsed = 0
    while elapsed < timeout:
        status = policy.get_approval_status(approval_id)
        if status == "approved":
            return True
        if status == "denied":
            return False
        await asyncio.sleep(2)
        elapsed += 2
    policy.expire_approval(approval_id)
    return False
