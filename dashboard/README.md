# Armoriq Guardrails Dashboard

Admin dashboard for the Guarded AI Agent. Provides real-time monitoring and control over the agent's policy enforcement.

## Pages

| Page | Description |
|------|-------------|
| **Rules** | Create, toggle, and delete guardrail rules (BLOCK_TOOL, REQUIRE_APPROVAL, VALIDATE_INPUT, BLOCK_KEYWORD) |
| **Logs** | Real-time WebSocket stream of all tool calls with expandable argument/result details |
| **Approvals** | Auto-refreshing queue for pending human approval requests with Approve/Deny actions |
| **Stats** | Token usage cards, enforcement rate bar, conversation and tool call counts |

## Setup

```bash
cd dashboard
npm install
npm run dev
```

The dashboard runs at `http://localhost:5173` and expects the backend at `http://localhost:8000`.

## Build

```bash
npm run build
# Output in dist/
```

## Tech Stack

- React 19
- TypeScript
- Vite 8
- Vanilla CSS (dark theme)
- React Router DOM
