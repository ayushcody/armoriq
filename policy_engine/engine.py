"""
Policy evaluation engine.
Supports BLOCK_TOOL, REQUIRE_APPROVAL, VALIDATE_INPUT, BLOCK_KEYWORD rule types.
Includes built-in prompt injection detection.
"""

import fnmatch, uuid, json, logging, re
from datetime import datetime
from .models import PolicyRule
from .rule_store import RuleStore

logger = logging.getLogger(__name__)

# Always-on injection patterns (regardless of BLOCK_KEYWORD rules)
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all rules",
    "you are now",
    "pretend you are",
    "disregard your",
    "override policy",
    "bypass guardrail",
    "forget your instructions",
    "act as if you have no",
    "jailbreak",
    "developer mode",
    "do anything now",
    "dan mode",
]


class PolicyEngine:
    def __init__(self, store: RuleStore):
        self._store = store
        self._rules: list[PolicyRule] = store.load_all()
        self._approvals: dict[str, dict] = {}  # approval_id -> metadata dict
        self.panic_mode = False  # The "Creative" bonus: Global lockdown state
        store.on_change(self._on_rules_changed)
        logger.info(f"PolicyEngine initialized with {len(self._rules)} rules")

    def _on_rules_changed(self):
        """Called by RuleStore watcher thread when rules change in DB."""
        self._rules = self._store.load_all()
        logger.info(f"PolicyEngine: hot-reloaded {len(self._rules)} rules")

    def detect_injection(self, text: str) -> str | None:
        """Bonus: Check raw text for prompt injection patterns."""
        t = text.lower()
        for pattern in INJECTION_PATTERNS:
            if pattern in t:
                return f"Prompt injection pattern detected: '{pattern}'"
        return None

    def evaluate(self, tool_call: dict) -> dict:
        """
        Called by agent_loop for every tool call before execution.
        Priority: PANIC_MODE > BLOCK_KEYWORD > BLOCK_TOOL > REQUIRE_APPROVAL
        """
        if self.panic_mode:
            return {
                "action": "BLOCK",
                "reason": "SYSTEM IN PANIC MODE: All tool execution is globally suspended for security.",
                "rule_id": "builtin:panic_lock"
            }

        name = tool_call["name"]
        args = tool_call["args"]

        # Creative Bonus: Handle the Panic Trigger itself
        if name == "trigger_panic_mode":
            self.panic_mode = True
            return {"action": "ALLOW"}

        args_str = json.dumps(args).lower()
        enabled = [r for r in self._rules if r.enabled]

        # 1. Always check for prompt injection in arguments
        injection_error = self.detect_injection(args_str)
        if injection_error:
            return {
                "action": "BLOCK",
                "reason": injection_error,
                "rule_id": "builtin:injection_guard"
            }

        # 2. BLOCK_KEYWORD rules (custom keywords from admin)
        for rule in enabled:
            if rule.type != "BLOCK_KEYWORD":
                continue
            keywords = [k.lower() for k in rule.config.get("keywords", [])]
            mode = rule.config.get("match_mode", "any")
            matched = [k for k in keywords if k in args_str]
            if (mode == "any" and matched) or (mode == "all" and len(matched) == len(keywords)):
                return {
                    "action": "BLOCK",
                    "reason": f"Blocked keyword matched in tool arguments",
                    "rule_id": rule.id
                }

        # 3. BLOCK_TOOL (supports glob patterns e.g. "trigger_*", "scale_*")
        for rule in enabled:
            if rule.type != "BLOCK_TOOL":
                continue
            pattern = rule.config.get("tool_name", "")
            if fnmatch.fnmatch(name, pattern):
                return {
                    "action": "BLOCK",
                    "reason": f"Tool '{name}' is blocked by rule '{rule.name}'",
                    "rule_id": rule.id
                }

        # 4. REQUIRE_APPROVAL
        for rule in enabled:
            if rule.type != "REQUIRE_APPROVAL":
                continue
            pattern = rule.config.get("tool_name", "")
            if fnmatch.fnmatch(name, pattern):
                approval_id = str(uuid.uuid4())
                reason = f"Tool '{name}' requires human approval (rule: {rule.name})"
                self._approvals[approval_id] = {
                    "approval_id": approval_id,
                    "status": "pending",
                    "tool_name": name,
                    "arguments": args,
                    "rule_id": rule.id,
                    "reason": reason,
                    "created_at": datetime.utcnow().isoformat(),
                }
                return {
                    "action": "REQUIRE_APPROVAL",
                    "reason": reason,
                    "rule_id": rule.id,
                    "approval_id": approval_id,
                    "timeout": rule.config.get("approval_timeout_seconds", 300)
                }

        # 5. VALIDATE_INPUT
        for rule in enabled:
            if rule.type != "VALIDATE_INPUT":
                continue
            pattern = rule.config.get("tool_name", "")
            if not fnmatch.fnmatch(name, pattern):
                continue
            violation = self._check_validation(args, rule.config)
            if violation:
                return {
                    "action": "BLOCK",
                    "reason": violation,
                    "rule_id": rule.id
                }

        return {"action": "ALLOW"}

    def _check_validation(self, args: dict, config: dict) -> str | None:
        field = config.get("field_path")
        rule_str = config.get("rule", "")
        value = args.get(field)
        if value is None:
            return None
        if rule_str.startswith("max_value:"):
            limit = int(rule_str.split(":")[1])
            if isinstance(value, (int, float)) and value > limit:
                return f"Field '{field}' value {value} exceeds maximum allowed {limit}"
        elif rule_str.startswith("allowlist:"):
            allowed = json.loads(rule_str.split(":", 1)[1])
            if value not in allowed:
                return f"Field '{field}' value '{value}' not in allowlist: {allowed}"
        elif rule_str.startswith("regex:"):
            pattern = rule_str.split(":", 1)[1]
            if not re.match(pattern, str(value)):
                return f"Field '{field}' value '{value}' does not match required pattern"
        return None

    # --- Approval management ---
    def get_approval_status(self, approval_id: str) -> str:
        item = self._approvals.get(approval_id)
        return item["status"] if item else "unknown"

    def resolve_approval(self, approval_id: str, decision: str):
        if approval_id in self._approvals:
            self._approvals[approval_id]["status"] = decision

    def expire_approval(self, approval_id: str):
        if approval_id in self._approvals:
            self._approvals[approval_id]["status"] = "denied"

    def get_pending_approvals(self) -> list[dict]:
        return [
            item for item in self._approvals.values()
            if item.get("status") == "pending"
        ]

    # --- CRUD (called by dashboard API, persisted via rule_store) ---
    def create_rule(self, rule: PolicyRule) -> PolicyRule:
        self._store.save(rule)
        return rule

    def update_rule(self, rule: PolicyRule) -> PolicyRule:
        rule.updated_at = datetime.utcnow().isoformat()
        self._store.save(rule)
        return rule

    def delete_rule(self, rule_id: str):
        self._store.delete(rule_id)

    def toggle_rule(self, rule_id: str, enabled: bool) -> PolicyRule | None:
        rule = next((r for r in self._rules if r.id == rule_id), None)
        if rule:
            rule.enabled = enabled
            rule.updated_at = datetime.utcnow().isoformat()
            self._store.save(rule)
        return rule

    def list_rules(self) -> list[PolicyRule]:
        return list(self._rules)
