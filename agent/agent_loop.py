"""
Agent loop — core tool-use conversation loop with policy intercept.
"""

import json, asyncio, logging, uuid
from datetime import datetime

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Guarded AI Assistant for Research and DevOps.
Your goal is to provide accurate, cited information and manage infrastructure health.
Use the provided tools whenever you need to search the web or check system status.
CRITICAL: You must use the tool-calling API. Never, under any circumstances, generate <function=> tags or text-based tool calls.
When a tool is blocked by policy, explain this clearly to the user."""


async def run_conversation(
    user_message: str,
    llm,           # LLMClient
    registry,      # MCPRegistry
    policy,        # PolicyEngine
    log_store,     # LogStore
    conversation_id: str | None = None,
) -> dict:
    try:
        return await asyncio.wait_for(
            _run_conversation_internal(user_message, llm, registry, policy, log_store, conversation_id),
            timeout=60.0
        )
    except Exception as e:
        # Check if this is the notorious Groq tool-calling glitch
        error_str = str(e)
        if "failed_generation" in error_str and "<function=" in error_str:
            logger.warning("CATCHING GROQ GLITCH: Attempting auto-repair...")
            try:
                # Bulletproof Parser for Groq Glitches
                import re
                # Match name and everything until the last </function>
                match = re.search(r"<function=([\w\-_>]+)[\s=]*(.*)", error_str, re.DOTALL)
                if match:
                    fn_name = match.group(1).split(">")[0].strip() # Clean name of any >
                    raw_block = match.group(2).strip()
                    
                    # Strip the closing tag if it exists (at any position)
                    raw_args = re.sub(r"</function.*?>", "", raw_block, flags=re.DOTALL).strip()
                    
                    fn_args = {}
                    if raw_args:
                        try:
                            # 1. Try standard JSON first
                            start = raw_args.find('{')
                            end = raw_args.rfind('}')
                            if start != -1 and end != -1:
                                fn_args = json.loads(raw_args[start:end+1])
                            else:
                                # 2. Try parsing as a raw string (sometimes Groq just puts the query text there)
                                try:
                                    parsed = json.loads(raw_args)
                                    if isinstance(parsed, str):
                                        if fn_name in ["search_web", "get_web_answer"]: fn_args = {"query": parsed}
                                        elif fn_name == "trigger_panic_mode": fn_args = {"reason": parsed}
                                        else: fn_args = {"service_name": parsed}
                                    else:
                                        fn_args = parsed
                                except:
                                    # 3. Fallback: Regex for key="value" or key=value
                                    pairs = re.findall(r'([\w\-]+)\s*=\s*(?:"([^"]*)"|(\S+))', raw_args)
                                    for key, val1, val2 in pairs:
                                        fn_args[key] = val1 if val1 else val2
                                    
                                    # 4. Final Fallback: If still empty, treat the whole thing as a query
                                    if not fn_args and len(raw_args) > 2:
                                        clean_raw = raw_args.strip(' "\'>=')
                                        if fn_name in ["search_web", "get_web_answer"]: fn_args = {"query": clean_raw}
                                        else: fn_args = {"service_name": clean_raw}
                        except Exception as parse_err:
                            logger.warning(f"Repair parser failed: {parse_err}")
                    
                    # Auto-correct hallucinated argument names
                    if isinstance(fn_args, dict):
                        if fn_name in ["search_web", "get_web_answer"] and "query" not in fn_args:
                            for k, v in fn_args.items():
                                if isinstance(v, str):
                                    fn_args["query"] = v
                                    break
                    
                    # Manual Intercept & Execute
                    decision = policy.evaluate({"name": fn_name, "args": fn_args})
                    if decision["action"] == "ALLOW":
                        result = await registry.call_tool(fn_name, fn_args)
                        
                        # Perfect Reply: Pass the repaired data back to the LLM for a natural response
                        messages.append({"role": "assistant", "content": f"<function={fn_name}>{json.dumps(fn_args)}</function>"})
                        messages.append({"role": "tool", "tool_call_id": "repair-id", "name": fn_name, "content": json.dumps(result)})
                        
                        final_response = await llm.chat(messages)
                        return {
                            "reply": final_response.choices[0].message.content,
                            "conversation_id": conversation_id or "repair-mode",
                            "tool_calls": [{"tool_name": fn_name, "summary": f"Repaired {fn_name}", "policy_decision": "REPAIRED"}],
                            "tokens": {"prompt": 0, "completion": 0},
                            "backend": "groq_repair_shield"
                        }
            except Exception as repair_err:
                logger.error(f"Repair shield failed to execute tool: {repair_err}")
                return {
                    "reply": f"⚠️ Tool execution failed during auto-repair: {str(repair_err)}. Ensure your arguments are valid.",
                    "conversation_id": conversation_id or "repair-mode",
                    "tool_calls": [{"tool_name": "unknown", "summary": "Auto-repair execution failed", "policy_decision": "ERROR"}],
                    "tokens": {"prompt": 0, "completion": 0},
                    "backend": "error_handler"
                }

        logger.error(f"Conversation error: {e}")
        return {
            "reply": f"⚠️ System Error: {error_str}. Please try re-phrasing your request.",
            "conversation_id": conversation_id or "error",
            "tool_calls": [],
            "tokens": {"prompt": 0, "completion": 0},
            "backend": "error_handler"
        }

async def _run_conversation_internal(
    user_message: str,
    llm,
    registry,
    policy,
    log_store,
    conversation_id: str | None = None,
) -> dict:
    conversation_id = conversation_id or str(uuid.uuid4())
    
    # Bonus: Pre-emptive Injection Shield (Guardrail Bonus)
    injection_error = policy.detect_injection(user_message)
    if injection_error:
        logger.warning(f"BLOCKED raw prompt injection: {user_message}")
        return {
            "reply": f"Guardrail Alert: Your message was flagged as a potential prompt injection attack. Action blocked. Reason: {injection_error}",
            "conversation_id": conversation_id,
            "tool_calls": [],
            "tokens": {"prompt": 0, "completion": 0},
            "backend": "guardrail_active",
        }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]
    tools = registry.get_all_tools()
    if not tools:
        return {
            "reply": "⚠️ System Warning: No MCP tools were discovered. The agent is currently in 'Safe Mode' and cannot execute DevOps or Search actions. Please try hitting the 'Sync/Reload' button in the Discovered Tools modal.",
            "conversation_id": conversation_id,
            "tool_calls": [],
            "tokens": {"prompt": 0, "completion": 0},
            "backend": "no_tools_found"
        }
    total_tokens = {"prompt": 0, "completion": 0}
    tool_calls_log = []

    while True:
        response = await llm.chat(messages=messages, tools=tools if tools else None)

        # Track tokens
        usage = response.usage
        if usage:
            total_tokens["prompt"]     += usage.prompt_tokens or 0
            total_tokens["completion"] += usage.completion_tokens or 0

        choice = response.choices[0]
        msg = choice.message

        # Final answer — no more tool calls
        if choice.finish_reason == "stop" or not msg.tool_calls:
            final_content = msg.content or "The agent has completed the task without additional commentary."
            await log_store.save_conversation(conversation_id, tool_calls_log, total_tokens)
            return {
                "reply": final_content,
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

            # Generate human-readable summary
            summary = f"Called {fn_name}"
            if fn_name == "search_web" or fn_name == "get_web_answer":
                summary = f"Searching for '{fn_args.get('query')}'"
            elif fn_name == "get_page_contents":
                summary = f"Crawling {len(fn_args.get('urls', []))} URLs"
            elif fn_name == "scale_service":
                summary = f"Scaling {fn_args.get('service_name')} to {fn_args.get('replicas')} replicas"
            elif fn_name == "get_service_logs":
                summary = f"Fetching logs for {fn_args.get('service_name')}"
            elif fn_name == "run_healthcheck":
                summary = f"Checking health of {fn_args.get('service_name')}"
            elif fn_name == "trigger_alert":
                summary = f"Alerting: {fn_args.get('message')[:30]}..."

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "conversation_id": conversation_id,
                "tool_name": fn_name,
                "summary": summary,
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
            safe_content = tool_result if isinstance(tool_result, str) else json.dumps(tool_result, default=str)
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": safe_content,
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
