"""
Mock data for the DevOps Sentinel MCP server.
In-memory fake infrastructure data for demonstration.
"""

SERVICES = {
    "auth-service":    {"status": "healthy",  "replicas": 3, "cpu": 12, "mem_mb": 340},
    "payment-service": {"status": "degraded", "replicas": 2, "cpu": 78, "mem_mb": 890},
    "api-gateway":     {"status": "healthy",  "replicas": 5, "cpu": 23, "mem_mb": 512},
    "ml-inference":    {"status": "down",     "replicas": 0, "cpu": 0,  "mem_mb": 0},
    "log-aggregator":  {"status": "healthy",  "replicas": 1, "cpu": 5,  "mem_mb": 128},
}

LOGS = {
    "auth-service": [
        "2024-01-15 10:23:01 INFO  Token validated for user=admin@armoriq.io",
        "2024-01-15 10:23:45 WARN  Rate limit approaching: 890/1000 req/min",
        "2024-01-15 10:24:02 ERROR Failed login attempt from IP 192.168.1.55",
    ],
    "payment-service": [
        "2024-01-15 10:20:00 ERROR DB connection timeout after 30s",
        "2024-01-15 10:20:01 WARN  Retrying DB connection (attempt 3/5)",
        "2024-01-15 10:21:00 ERROR Circuit breaker OPEN — payment processor unreachable",
    ],
    "api-gateway":   ["2024-01-15 10:24:00 INFO  Routed 1200 requests in last 60s"],
    "ml-inference":  ["2024-01-15 09:00:00 ERROR OOM kill signal received — pod evicted"],
    "log-aggregator":["2024-01-15 10:24:01 INFO  Ingested 45MB logs in last minute"],
}

ALERTS = []  # mutated by trigger_alert tool calls
