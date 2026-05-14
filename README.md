# Armoriq Guarded Agent

A full-stack implementation of a robust, policy-enforced AI Agent using the Model Context Protocol (MCP). The Guarded Agent dynamically discovers infrastructure management tools, executes them autonomously to fulfill user requests, and strictly adheres to real-time administrative guardrails.

## 🚀 Key Features

*   **Dynamic Tool Discovery:** Zero hardcoded tools. The agent automatically discovers schemas from connected MCP servers (e.g., custom DevOps plugins, Web Search) at runtime.
*   **Real-time Policy Interception:** Every single tool execution request made by the LLM is intercepted and evaluated by a standalone `PolicyEngine` before reaching the execution layer.
*   **Human-in-the-Loop:** Supports `REQUIRE_APPROVAL` policies, pausing agent execution and pushing requests to the dashboard for administrative sign-off.
*   **Built-in Injection Protection:** Automatically scans AI tool argument payloads for jailbreak and prompt-injection patterns, shutting down rogue behavior instantly.
*   **Hot-Reloading:** Policy rules added or toggled in the React dashboard instantly apply to active, running agent loops without requiring a restart.

---

## 🏗️ Architecture

The codebase is divided into four strictly isolated modules:

1.  **`agent/` (FastAPI Backend)**
    *   Manages the LLM orchestration via the `LLMClient` (Strictly configured for Groq).
    *   Hosts the REST API and WebSocket streams for real-time frontend logs.
    *   Manages the `MCPRegistry` to maintain connections with underlying tool servers.
2.  **`policy_engine/` (Standalone Guardrails)**
    *   A completely decoupled evaluation engine running against SQLite rules. 
    *   Enforces `BLOCK_TOOL`, `REQUIRE_APPROVAL`, `BLOCK_KEYWORD`, and `VALIDATE_INPUT` schemas.
3.  **`custom_mcp_server/` (Mock Infrastructure Manager)**
    *   A plug-and-play Python MCP Server implementing JSON-RPC 2.0 over standard I/O.
    *   Exposes 5 DevOps tools: `list_services`, `get_service_logs`, `scale_service`, `trigger_alert`, `run_healthcheck`.
4.  **`dashboard/` (React SPA UI)**
    *   Vite + React frontend for monitoring agent stats, resolving pending approvals, toggling policy rules, and streaming live tool-call logs.

---

## 🛠️ Local Development (Docker Compose)

The easiest way to spin up the entire stack locally is using Docker Compose.

### Prerequisites
*   Docker & Docker Compose installed.

### Start the Stack
1. Clone the repository:
   ```bash
   git clone https://github.com/ayushcody/armoriq.git
   cd armoriq
   ```
2. Start the services:
   ```bash
   docker-compose up -d --build
   ```
3. Access the dashboard:
   Navigate to `http://localhost:5173` in your browser.
4. Provide your **Groq API Key** via the Dashboard configuration panel to activate the AI.

### Interacting with the Agent
With the dashboard running, you can open a terminal and simulate user chats. The backend runs on port `8000`.

```bash
# Ask the agent to check infrastructure status
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "List all services and their status"}'
```

Watch the Dashboard's **Logs** page to see the `ALLOW` event and the tool payload. To test the guardrails, add a `BLOCK_TOOL` rule for `get_service_logs` in the dashboard, and then attempt to fetch logs!

---

## 🚀 Deployment Guide

This project is built to be deployed seamlessly using modern PaaS providers.

### 1. Backend (FastAPI + MCP Server) ➡️ Render.com
1. Create a Web Service on Render and point it to your GitHub repository.
2. Select **Docker** as your environment.
3. Set the **Dockerfile Path** to `agent/Dockerfile`.
4. Deploy. Copy your live Render URL (e.g., `https://armoriq-backend.onrender.com`).

### 2. Frontend (React Dashboard) ➡️ Vercel
1. Create a new project on Vercel and import your repository.
2. Set the **Root Directory** to `dashboard/`.
3. Add the following Environment Variables in Vercel settings:
   *   `VITE_API_URL`: Your Render backend URL (e.g., `https://armoriq-backend.onrender.com`)
   *   `VITE_WS_URL`: Your Render WebSockets URL (e.g., `wss://armoriq-backend.onrender.com/ws/logs`)
4. Deploy!
